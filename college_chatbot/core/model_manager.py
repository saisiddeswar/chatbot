
import os
import pickle
import joblib
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from core.logger import get_logger
import shutil


logger = get_logger("model_manager")

class ModelManager:
    """
    Centralized manager for lazy-loading heavy models and resources.
    Ensures that RAM is not consumed until necessary.
    Singleton pattern for shared resources.
    """
    _embedder = None
    _classifier = None
    
    # Bot 2 resources
    _bot2_index = None
    _bot2_qa_pairs = None
    
    # Bot 3 resources
    _bot3_index = None
    _bot3_metadata = None

    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    @classmethod
    def _get_abs_path(cls, rel_path: str) -> str:
        return os.path.join(cls.BASE_DIR, rel_path)

    @classmethod
    def get_embedder(cls) -> SentenceTransformer:
        """Lazy load shared embedding model."""
        if cls._embedder is None:
            logger.info("Lazy-loading embedding model (all-MiniLM-L6-v2)...")
            try:
                cls._embedder = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info("[OK] Embedding model loaded.")
            except Exception as e:
                logger.error(f"Failed to load embedding model: {e}")
                raise
        return cls._embedder

    @classmethod
    def get_classifier(cls):
        """Lazy load intent classifier."""
        if cls._classifier is None:
            path = cls._get_abs_path("classifier/classifier.pkl")
            if os.path.exists(path):
                logger.info(f"Lazy-loading classifier from {path}...")
                try:
                    cls._classifier = joblib.load(path)
                    logger.info("[OK] Classifier loaded.")
                except Exception as e:
                    logger.error(f"Failed to load classifier: {e}")
                    raise
            else:
                logger.warning(f"Classifier not found at {path}. Using fallback/mock if allowed.")
                # We might return None, let caller handle it
                return None
        return cls._classifier

    # Cache for separate domain indices: {domain_name: (index, qa_pairs)}
    _domain_resources = {}

    @classmethod
    def get_domain_qa_resources(cls, domain_name: str = None):
        """
        Lazy load specific domain QA resources.
        If domain_name is None or not found, defaults to 'general'.
        """
        # Map category names to folder names
        DOMAIN_MAP = {
            "Admissions & Registrations": "admissions",
            "Financial Matters": "financial",
            "Academic Affairs": "academic",
            "Student Services": "student_services",
            "Campus Life": "campus_life",
            "General Information": "general",
            "Cross-Domain Queries": "cross_domain"
        }
        
        # Case-insensitive lookup
        if domain_name:
            # Try direct match
            target_folder = DOMAIN_MAP.get(domain_name)
            
            # Try case-insensitive
            if not target_folder:
                domain_lower = domain_name.lower()
                # Create lower map
                lower_map = {k.lower(): v for k, v in DOMAIN_MAP.items()}
                target_folder = lower_map.get(domain_lower, "general")
        else:
            target_folder = "general"
        
        if target_folder in cls._domain_resources:
            return cls._domain_resources[target_folder]
            
        # Path construction
        # embeddings/domains/{folder}/qa_index.faiss
        base_path = cls._get_abs_path(f"embeddings/domains/{target_folder}")
        index_path = os.path.join(base_path, "qa_index.faiss")
        qa_path = os.path.join(base_path, "qa_metadata.pkl")
        
        # Check if resources exist, if not, attempt rebuild
        if not (os.path.exists(index_path) and os.path.exists(qa_path)):
            logger.warning(f"Resources missing for '{target_folder}'. Attempting automatic rebuild...")
            cls.rebuild_domain_indices()
        
        logger.info(f"Lazy-loading domain resources for '{target_folder}'...")
        
        index = None
        qa_pairs = []
        
        if os.path.exists(index_path) and os.path.exists(qa_path):
            try:
                index = faiss.read_index(index_path)
                with open(qa_path, "rb") as f:
                    qa_pairs = pickle.load(f)
                
                # VALIDATION LOGS
                logger.info(f"STATUS REPORT: Bot-2 Resources for '{target_folder}'")
                logger.info(f"  - FAISS Index Vectors: {index.ntotal}")
                logger.info(f"  - QA Entries Loaded: {len(qa_pairs)}")
                
                if len(qa_pairs) == 0:
                     logger.error(f"CRITICAL: QA dataset for '{target_folder}' is empty!")
                     return None, []
                     
            except Exception as e:
                logger.error(f"Failed to load {target_folder} resources: {e}")
                import traceback
                logger.error(traceback.format_exc())
        else:
            logger.error(f"CRITICAL: Failed to build/find resources for {target_folder} at {base_path}")
            return None, []
            
        cls._domain_resources[target_folder] = (index, qa_pairs)
        return index, qa_pairs

    @classmethod
    def rebuild_domain_indices(cls):
        """
        Rebuilds FAISS indices for all domains from data/qa_dataset.csv.
        """
        import pandas as pd
        
        logger.info("--------------------------------------------------")
        logger.info("STARTING AUTOMATIC FAISS INDEX BUILD")
        logger.info("--------------------------------------------------")
        
        csv_path = cls._get_abs_path("data/qa_dataset.csv")
        if not os.path.exists(csv_path):
            logger.error(f"QA Dataset not found at {csv_path}")
            return False
            
        try:
            df = pd.read_csv(csv_path)
            # Normalize column names just in case
            df.columns = [c.lower().strip() for c in df.columns] 
            
            if "domain" not in df.columns or "question" not in df.columns or "answer" not in df.columns:
                 logger.error(f"CSV missing required columns. Found: {df.columns}")
                 return False

            # Group by domain
            DOMAIN_MAP = {
                "Admissions & Registrations": "admissions",
                "Financial Matters": "financial",
                "Academic Affairs": "academic",
                "Student Services": "student_services",
                "Campus Life": "campus_life",
                "General Information": "general",
                "Cross-Domain Queries": "cross_domain"
            }
            
            # Helper to normalize domain string from CSV
            def normalize_domain_key(d):
                return d.strip() if isinstance(d, str) else "General Information"

            embedder = cls.get_embedder()
            
            grouped = df.groupby(df['domain'].apply(normalize_domain_key))
            
            total_indices_built = 0
            
            for domain, group in grouped:
                target_folder = DOMAIN_MAP.get(domain, "general")
                
                logger.info(f"Building index for domain: '{domain}' -> '{target_folder}'")
                
                # Prepare data
                questions = group["question"].fillna("").tolist()
                answers = group["answer"].fillna("").tolist()
                domains_list = group["domain"].fillna("General Information").tolist()
                
                if not questions:
                    logger.warning(f"No questions for domain {domain}, skipping.")
                    continue
                
                # Embed
                logger.info(f"  - Generating embeddings for {len(questions)} items...")
                embeddings = embedder.encode(questions, show_progress_bar=False)
                embeddings = np.array(embeddings).astype("float32")
                
                # Build Index
                d = embeddings.shape[1]
                index = faiss.IndexFlatL2(d)
                index.add(embeddings)
                
                # Metadata
                qa_metadata = []
                for q, a, dom in zip(questions, answers, domains_list):
                    qa_metadata.append({
                        "question": q,
                        "answer": a,
                        "domain": dom
                    })
                
                # Save
                base_dir = cls._get_abs_path(f"embeddings/domains/{target_folder}")
                if os.path.exists(base_dir):
                    shutil.rmtree(base_dir) # Clean existing
                os.makedirs(base_dir, exist_ok=True)
                
                faiss.write_index(index, os.path.join(base_dir, "qa_index.faiss"))
                with open(os.path.join(base_dir, "qa_metadata.pkl"), "wb") as f:
                    pickle.dump(qa_metadata, f)
                    
                logger.info(f"  - [SUCCESS] Built {target_folder} index. Config: {len(qa_metadata)} vectors.")
                total_indices_built += 1
                
            logger.info(f"Auto-build completed. Rebuilt {total_indices_built} indices.")
            return True
            
        except Exception as e:
            logger.exception(f"Failed to rebuild indices: {e}")
            return False

    @classmethod
    def get_bot2_resources(cls):
        """
        Legacy Accessor - defaults to 'general' or aggregated if we had one.
        For backward compatibility, let's just return 'general'.
        """
        return cls.get_domain_qa_resources("General Information")

    @classmethod
    def get_bot3_resources(cls):
        """
        Lazy load Bot-3 FAISS index and Metadata.
        Returns: (index, metadata)
        """
        if cls._bot3_index is None or cls._bot3_metadata is None:
            index_path = cls._get_abs_path("embeddings/bot3_faiss_NEW/index.faiss")
            meta_path = cls._get_abs_path("embeddings/bot3_faiss_NEW/metadata.pkl")
            
            logger.info("Lazy-loading Bot-3 resources...")
            
            # Load Index
            if os.path.exists(index_path):
                try:
                    cls._bot3_index = faiss.read_index(index_path)
                    logger.info(f"[OK] Bot-3 FAISS index loaded ({cls._bot3_index.ntotal} items).")
                except Exception as e:
                    logger.error(f"Failed to load Bot-3 FAISS index: {e}")
                    cls._bot3_index = None
            else:
                logger.warning(f"Bot-3 index missing at {index_path}")
                cls._bot3_index = None
                
            # Load Metadata
            if os.path.exists(meta_path):
                try:
                    with open(meta_path, "rb") as f:
                        cls._bot3_metadata = pickle.load(f)
                    logger.info(f"[OK] Bot-3 metadata loaded ({len(cls._bot3_metadata)} items).")
                except Exception as e:
                    logger.error(f"Failed to load Bot-3 metadata: {e}")
                    cls._bot3_metadata = []
            else:
                logger.warning(f"Bot-3 metadata missing at {meta_path}")
                cls._bot3_metadata = []
                
        return cls._bot3_index, cls._bot3_metadata

    # Rule-based Bot resources
    _aiml_kernel = None

    @classmethod
    def get_aiml_kernel(cls):
        """
        Lazy load AIML kernel for rule-based bot.
        """
        import aiml
        
        if cls._aiml_kernel is None:
            logger.info("Lazy-loading AIML kernel...")
            kernel = aiml.Kernel()
            
            # Load AIML files
            aiml_files = [
                "data/aiml/rvrjcce_comprehensive.aiml"
            ]
            
            loaded_count = 0
            for aiml_path in aiml_files:
                if os.path.exists(aiml_path):
                    try:
                        kernel.learn(aiml_path)
                        loaded_count += 1
                        logger.info(f"[OK] Loaded AIML file: {aiml_path}")
                    except Exception as e:
                        logger.error(f"Error loading AIML file {aiml_path}: {e}")
                else:
                    logger.warning(f"AIML file not found at {aiml_path}")
            
            cls._aiml_kernel = kernel
            logger.info(f"[OK] AIML kernel ready ({loaded_count} files loaded).")
            
        return cls._aiml_kernel
