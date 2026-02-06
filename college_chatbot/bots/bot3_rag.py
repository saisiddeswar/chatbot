"""
Bot-3: Retrieval-Augmented Generation (RAG) with Full Implementation.

Features:
- Document loading and chunking with overlap
- Metadata storage (source, chunk index)
- FAISS vector retrieval with confidence scoring
- Retrieval verification (no hallucination)
- Context management with limits
- Full audit logging

This is the "last resort" bot that should ONLY be used when:
1. Rule-bot has no answer
2. Bot-2 similarity is too low
3. Query confidence is low
"""

import json
import os
import pickle
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional, Tuple

import faiss
import numpy as np
from config.settings import settings
from core.audit_logger import get_audit_logger
from core.logger import get_logger
from sentence_transformers import SentenceTransformer

logger = get_logger("bot3")
audit_logger = get_audit_logger("bot3")

# ============== CONFIGURATION ==============
INDEX_DIR = "embeddings/bot3_faiss"
INDEX_FILE = os.path.join(INDEX_DIR, "index.faiss")
METADATA_FILE = os.path.join(INDEX_DIR, "metadata.pkl")
DATA_DIR = "data/bot3_docs"

# ============== DATA STRUCTURES ==============

@dataclass
class Document:
    """Represents a source document."""
    source: str  # filename or URL
    content: str  # full text
    doc_type: str = "text"  # text, pdf, website


@dataclass
class Chunk:
    """Represents a document chunk with metadata."""
    text: str
    source: str
    chunk_id: int
    chunk_size: int
    start_char: int
    end_char: int
    embedding: Optional[np.ndarray] = None


# ============== EMBEDDING MODEL ==============
try:
    embed_model = SentenceTransformer("all-MiniLM-L6-v2")
    logger.info("[OK] Embedding model loaded: all-MiniLM-L6-v2")
except Exception as e:
    logger.error(f"[ERROR] Failed to load embedding model: {e}")
    embed_model = None


# ============== DOCUMENT LOADING ==============

def load_documents_from_directory(data_dir: str) -> List[Document]:
    """
    Load all documents from data directory.
    
    Supports: .txt files (scraped content)
    """
    documents = []
    
    if not os.path.exists(data_dir):
        logger.error(f"Data directory not found: {data_dir}")
        return documents
    
    # Load .txt files
    for filename in os.listdir(data_dir):
        if filename.endswith(".txt"):
            filepath = os.path.join(data_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        doc = Document(
                            source=filename,
                            content=content,
                            doc_type="text"
                        )
                        documents.append(doc)
                        logger.info(f"Loaded document: {filename} ({len(content)} chars)")
            except Exception as e:
                logger.error(f"Error loading {filename}: {e}")
    
    # Recursively load from subdirectories
    for subdir in os.listdir(data_dir):
        subpath = os.path.join(data_dir, subdir)
        if os.path.isdir(subpath) and not subdir.startswith("__"):
            documents.extend(load_documents_from_directory(subpath))
    
    logger.info(f"Total documents loaded: {len(documents)}")
    return documents


# ============== CHUNKING ==============

def chunk_document(doc: Document, chunk_size: int = None, overlap: int = None) -> List[Chunk]:
    """
    Chunk document into overlapping segments.
    
    Args:
        doc: Document to chunk
        chunk_size: Size of each chunk (default from settings)
        overlap: Overlap between chunks (default from settings)
    
    Returns:
        List of Chunk objects with metadata
    """
    if chunk_size is None:
        chunk_size = settings.CHUNK_SIZE
    if overlap is None:
        overlap = settings.CHUNK_OVERLAP
    
    chunks = []
    text = doc.content
    
    if len(text) < chunk_size:
        # Document is smaller than chunk size, don't split
        chunk = Chunk(
            text=text,
            source=doc.source,
            chunk_id=0,
            chunk_size=len(text),
            start_char=0,
            end_char=len(text)
        )
        chunks.append(chunk)
        return chunks
    
    # Slide window with overlap
    chunk_id = 0
    start = 0
    
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunk_text = text[start:end]
        
        chunk = Chunk(
            text=chunk_text,
            source=doc.source,
            chunk_id=chunk_id,
            chunk_size=len(chunk_text),
            start_char=start,
            end_char=end
        )
        chunks.append(chunk)
        
        chunk_id += 1
        # Move start by (chunk_size - overlap) to create overlap
        start = end - overlap
        
        if start >= len(text):
            break
    
    logger.debug(f"Chunked {doc.source}: {len(chunks)} chunks")
    return chunks


def chunk_all_documents(documents: List[Document]) -> List[Chunk]:
    """Chunk all documents."""
    all_chunks = []
    for doc in documents:
        chunks = chunk_document(doc)
        all_chunks.extend(chunks)
    
    logger.info(f"Total chunks created: {len(all_chunks)}")
    return all_chunks


# ============== FAISS INDEX MANAGEMENT ==============

def build_faiss_index(chunks: List[Chunk]) -> Tuple[faiss.Index, List[Dict]]:
    """
    Build FAISS index from chunks.
    
    Returns:
        (index: faiss.Index, metadata: List of chunk metadata)
    """
    if not chunks:
        logger.warning("No chunks to index")
        return faiss.IndexFlatL2(384), []
    
    if embed_model is None:
        logger.error("Embedding model not available")
        return faiss.IndexFlatL2(384), []
    
    logger.info(f"Building FAISS index for {len(chunks)} chunks...")
    
    # Embed all chunks
    texts = [chunk.text for chunk in chunks]
    embeddings = embed_model.encode(texts, show_progress_bar=True)
    embeddings = embeddings.astype(np.float32)
    
    # Create FAISS index (L2 distance)
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)
    
    # Store metadata for retrieval
    metadata = [
        {
            "text": chunk.text,
            "source": chunk.source,
            "chunk_id": chunk.chunk_id,
            "start_char": chunk.start_char,
            "end_char": chunk.end_char
        }
        for chunk in chunks
    ]
    
    logger.info(f"[OK] FAISS index built: {index.ntotal} vectors")
    return index, metadata


def load_or_build_index() -> Tuple[Optional[faiss.Index], Optional[List[Dict]]]:
    """
    Load existing FAISS index or build new one.
    
    Returns:
        (index, metadata) or (None, None) if failed
    """
    # Try to load existing index
    if os.path.exists(INDEX_FILE) and os.path.exists(METADATA_FILE):
        try:
            logger.info("Loading existing FAISS index...")
            index = faiss.read_index(INDEX_FILE)
            with open(METADATA_FILE, "rb") as f:
                metadata = pickle.load(f)
            logger.info(f"[OK] Loaded index with {index.ntotal} vectors")
            return index, metadata
        except Exception as e:
            logger.error(f"Error loading existing index: {e}")
    
    # Build new index
    try:
        logger.info("Building new FAISS index...")
        documents = load_documents_from_directory(DATA_DIR)
        chunks = chunk_all_documents(documents)
        
        if not chunks:
            logger.warning("No chunks to index, returning empty index")
            return faiss.IndexFlatL2(384), []
        
        index, metadata = build_faiss_index(chunks)
        
        # Save index and metadata
        os.makedirs(INDEX_DIR, exist_ok=True)
        faiss.write_index(index, INDEX_FILE)
        with open(METADATA_FILE, "wb") as f:
            pickle.dump(metadata, f)
        
        logger.info(f"[OK] Index saved to {INDEX_FILE}")
        return index, metadata
        
    except Exception as e:
        logger.error(f"Error building index: {e}")
        return None, None


# Load index on startup
faiss_index, metadata = load_or_build_index()


# ============== RETRIEVAL ==============

def retrieve_context(
    query: str,
    query_id: str,
    top_k: Optional[int] = None
) -> Tuple[List[Dict], float]:
    """
    Retrieve relevant chunks using FAISS.
    
    Returns:
        (retrieved_chunks: List[metadata dicts], confidence: float)
    """
    if faiss_index is None or faiss_index.ntotal == 0:
        logger.warning(f"[{query_id}] FAISS index not available")
        return [], 0.0
    
    if embed_model is None:
        logger.error(f"[{query_id}] Embedding model not available")
        return [], 0.0
    
    if top_k is None:
        top_k = settings.TOP_K_BOT3
    
    try:
        # Embed query
        query_embedding = embed_model.encode([query], show_progress_bar=False)
        query_embedding = query_embedding.astype(np.float32)
        
        # Search FAISS index
        distances, indices = faiss_index.search(query_embedding, top_k)
        distances = distances[0]
        indices = indices[0]
        
        logger.debug(f"[{query_id}] FAISS search - distances: {distances}, indices: {indices}")
        
        # Filter valid indices
        valid_results = []
        for dist, idx in zip(distances, indices):
            if idx >= 0 and idx < len(metadata):
                valid_results.append((dist, idx))
        
        if not valid_results:
            logger.info(f"[{query_id}] No valid results from FAISS search")
            return [], 0.0
        
        # Convert distances to confidence scores
        # L2 distance -> similarity: 1 / (1 + distance)
        max_distance = valid_results[0][0]  # Best (lowest) distance
        avg_distance = np.mean([d for d, _ in valid_results])
        max_confidence = 1.0 / (1.0 + max_distance)
        
        logger.info(
            f"[{query_id}] Retrieval - max_dist: {max_distance:.4f}, "
            f"avg_dist: {avg_distance:.4f}, confidence: {max_confidence:.4f}"
        )
        
        # Build result list
        retrieved = []
        for dist, idx in valid_results:
            chunk_meta = metadata[idx].copy()
            chunk_meta["distance"] = float(dist)
            chunk_meta["similarity"] = 1.0 / (1.0 + dist)
            retrieved.append(chunk_meta)
        
        # Log retrieval quality
        audit_logger.log_retrieval_quality(
            query_id=query_id,
            bot="BOT-3",
            top_k=top_k,
            scores=[float(d) for d, _ in valid_results],
            avg_score=float(max_confidence),
            passed_threshold=max_distance <= settings.BOT3_RETRIEVAL_THRESHOLD,
            threshold=settings.BOT3_RETRIEVAL_THRESHOLD,
            num_docs_retrieved=len(retrieved)
        )
        
        return retrieved, max_confidence
        
    except Exception as e:
        logger.exception(f"[{query_id}] Error in FAISS retrieval: {e}")
        audit_logger.log_error(
            query_id=query_id,
            error_type="RAG_RETRIEVAL_ERROR",
            error_message=str(e),
            stage="faiss_retrieval",
            stacktrace=str(e)
        )
        return [], 0.0


# ============== CONTEXT MANAGEMENT ==============

def build_context_window(
    retrieved_chunks: List[Dict],
    max_chars: Optional[int] = None
) -> str:
    """
    Build context window from retrieved chunks.
    Respects max character limit to avoid token overflow.
    """
    if max_chars is None:
        max_chars = settings.MAX_CONTEXT_CHARS_PER_TURN * settings.TOP_K_BOT3
    
    context_parts = []
    total_chars = 0
    
    for i, chunk in enumerate(retrieved_chunks, 1):
        # Format chunk with source info
        chunk_text = f"[Source: {chunk['source']}, Chunk {chunk['chunk_id']}]\n{chunk['text']}"
        
        if total_chars + len(chunk_text) > max_chars:
            logger.debug(f"Context limit reached, included {i-1} chunks")
            break
        
        context_parts.append(chunk_text)
        total_chars += len(chunk_text)
    
    context = "\n\n---\n\n".join(context_parts)
    
    logger.debug(f"Context built: {len(context)} chars from {len(context_parts)} chunks")
    return context


# ============== ANSWER GENERATION ==============

def bot3_answer(
    query: str,
    history: Optional[List[Tuple[str, str]]] = None,
    query_id: str = "unknown"
) -> str:
    """
    Generate answer using RAG pipeline.
    
    Returns:
        Answer string (grounded in retrieved context or fallback message)
    """
    logger.info(f"[{query_id}] Bot-3 (RAG) activated")
    
    if history is None:
        history = []
    
    # Limit history
    max_turns = settings.MAX_CONTEXT_TURNS
    limited_history = history[-max_turns:] if len(history) > max_turns else history
    
    logger.debug(f"[{query_id}] Using {len(limited_history)} historical turns")
    
    try:
        # 1) RETRIEVE
        retrieved_chunks, retrieval_confidence = retrieve_context(query, query_id)
        
        if not retrieved_chunks:
            logger.info(f"[{query_id}] No documents retrieved from FAISS")
            audit_logger.log_answer_rejection(
                query_id=query_id,
                bot="BOT-3",
                reason="No documents retrieved",
                score=0.0,
                threshold=settings.BOT3_RETRIEVAL_THRESHOLD
            )
            return (
                "[NO INFO] **No Official Information Found**\n\n"
                "I don't have information about this topic in the official college database. "
                "Please contact:\n"
                "- Student Services: [email/phone]\n"
                "- Registrar's Office: [email/phone]\n"
                "- Your Academic Advisor"
            )
        
        # 2) CHECK RETRIEVAL QUALITY
        if retrieval_confidence < settings.BOT3_MIN_CONFIDENCE:
            logger.info(
                f"[{query_id}] Retrieval confidence {retrieval_confidence:.4f} "
                f"below threshold {settings.BOT3_MIN_CONFIDENCE}"
            )
            audit_logger.log_answer_rejection(
                query_id=query_id,
                bot="BOT-3",
                reason="Low retrieval confidence",
                score=retrieval_confidence,
                threshold=settings.BOT3_MIN_CONFIDENCE
            )
            return (
                "[WARNING] **Low Confidence Answer**\n\n"
                "I found some related information, but I'm not confident it accurately "
                "answers your question. "
                "Please contact student services or check the official college website for accurate information."
            )
        
        # 3) BUILD CONTEXT
        context = build_context_window(retrieved_chunks)
        
        # 4) BUILD ANSWER (SIMPLE RULES-BASED, NO LLM)
        # Since the task says CPU-only and no cloud, we'll use simple template-based generation
        # with the retrieved context
        
        answer = generate_answer_from_context(
            query=query,
            context=context,
            retrieved_chunks=retrieved_chunks,
            confidence=retrieval_confidence,
            query_id=query_id
        )
        
        # 5) LOG SUCCESS
        audit_logger.log_answer_generation(
            query_id=query_id,
            bot="BOT-3",
            answer_length=len(answer),
            confidence=retrieval_confidence,
            sources=[chunk['source'] for chunk in retrieved_chunks],
            metadata={
                "retrieval_confidence": round(retrieval_confidence, 4),
                "num_chunks": len(retrieved_chunks)
            }
        )
        
        return answer
        
    except Exception as e:
        logger.exception(f"[{query_id}] Error in Bot-3 RAG: {e}")
        audit_logger.log_error(
            query_id=query_id,
            error_type="BOT3_RAG_ERROR",
            error_message=str(e),
            stage="rag_generation",
            stacktrace=str(e)
        )
        return f"[ERROR] Error generating answer: {str(e)}"


def generate_answer_from_context(
    query: str,
    context: str,
    retrieved_chunks: List[Dict],
    confidence: float,
    query_id: str
) -> str:
    """
    Generate answer from retrieved context using simple rules.
    
    Since we're CPU-only and want to avoid LLM hallucination,
    we extract and format answers directly from context.
    """
    
    if not context.strip():
        return "No relevant information found."
    
    # Simple answer generation:
    # 1. Extract first 2-3 sentences from most relevant chunk
    # 2. Add source attribution
    # 3. Add call-to-action
    
    best_chunk = retrieved_chunks[0]
    text = best_chunk['text']
    
    # Try to extract first few sentences
    sentences = [s.strip() for s in text.split('.') if s.strip()]
    answer_text = '.'.join(sentences[:3])
    if not answer_text.endswith('.'):
        answer_text += '.'
    
    # Format final answer with attribution
    answer = f"""{answer_text}

**Source:** {best_chunk['source']} (Chunk {best_chunk['chunk_id']})

---
**Confidence:** {'High' if confidence >= 0.75 else 'Medium' if confidence >= 0.5 else 'Low'}

_For more information, contact Student Services or visit the college website._
"""
    
    logger.info(f"[{query_id}] Generated answer from context ({len(answer)} chars)")
    
    return answer

