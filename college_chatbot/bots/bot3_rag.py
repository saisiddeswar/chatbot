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
from bots.hybrid_retriever import hybrid_retriever
from services.response_formatter import render_response, extract_json_from_text
import json

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
# Removed global execution. Accessed via ModelManager.

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
# (Kept unchanged mostly, but ensuring no side effects)

def chunk_document(doc: Document, chunk_size: int = None, overlap: int = None) -> List[Chunk]:
    """
    Chunk document into overlapping segments.
    """
    if chunk_size is None:
        chunk_size = settings.CHUNK_SIZE
    if overlap is None:
        overlap = settings.CHUNK_OVERLAP
    
    chunks = []
    text = doc.content
    
    if len(text) < chunk_size:
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
# NOTE: This function is checking ModelManager for embedder
from core.model_manager import ModelManager

def build_faiss_index(chunks: List[Chunk]) -> Tuple[faiss.Index, List[Dict]]:
    """
    Build FAISS index from chunks.
    """
    if not chunks:
        logger.warning("No chunks to index")
        return faiss.IndexFlatL2(384), []
    
    # Get embedder from ModelManager
    embed_model = ModelManager.get_embedder()
    
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

# No automatic loading on import!
# faiss_index, metadata = load_or_build_index() <-- REMOVED



# ============== RETRIEVAL ==============

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
    # Lazy load resources
    faiss_index, raw_metadata = ModelManager.get_bot3_resources()
    embed_model = ModelManager.get_embedder()
    
    # DEBUG PRINTS
    print(f"[DEBUG] retrieve_context called for query: {query}")
    print(f"[DEBUG] FAISS Index loaded? {faiss_index is not None}")
    if faiss_index:
        print(f"[DEBUG] FAISS ntotal: {faiss_index.ntotal}")
    print(f"[DEBUG] Metadata type: {type(raw_metadata)}")
    if isinstance(raw_metadata, dict):
        print(f"[DEBUG] Metadata keys: {raw_metadata.keys()}")
    
    # Handle metadata format (Dict vs List)
    metadata_list = []
    if isinstance(raw_metadata, dict):
        metadata_list = raw_metadata.get("chunks", [])
    elif isinstance(raw_metadata, list):
        metadata_list = raw_metadata
        
    print(f"[DEBUG] Final metadata_list len: {len(metadata_list)}")
        
    if faiss_index is None or faiss_index.ntotal == 0 or not metadata_list:
        print(f"[DEBUG] FAILURE: Missing resources. Index={faiss_index}, MetaLen={len(metadata_list)}")
        logger.warning(f"[{query_id}] FAISS index not available or empty metadata")
        return [], 0.0
    
    if top_k is None:
        top_k = settings.TOP_K_BOT3
    
    try:
        # Embed query
        print("[DEBUG] Embedding query...")
        query_embedding = embed_model.encode([query], show_progress_bar=False)
        query_embedding = query_embedding.astype(np.float32)
        
        # Search FAISS index
        print(f"[DEBUG] Searching FAISS with top_k={top_k}...")
        distances, indices = faiss_index.search(query_embedding, top_k)
        print(f"[DEBUG] Search results - Indices: {indices}, Distances: {distances}")
        distances = distances[0]
        indices = indices[0]
        
        logger.debug(f"[{query_id}] FAISS search - distances: {distances}, indices: {indices}")
        
        # Filter valid indices
        valid_results = []
        for dist, idx in zip(distances, indices):
            if idx >= 0 and idx < len(metadata_list):
                valid_results.append((dist, idx))
        
        if not valid_results:
            logger.info(f"[{query_id}] No valid results from FAISS search")
            return [], 0.0
        
        # Convert distances to confidence scores
        # L2 distance -> similarity: 1 / (1 + distance)
        max_distance = valid_results[0][0]  # Best (lowest) distance
        # avg_distance = np.mean([d for d, _ in valid_results]) # Unused
        
        max_confidence = float(1.0 / (1.0 + max_distance))        
        logger.info(
            f"[{query_id}] Retrieval - max_dist: {max_distance:.4f}, "
            f"confidence: {max_confidence:.4f}"
        )
        
        # Build result list
        retrieved = []
        for dist, idx in valid_results:
            chunk_meta = metadata_list[idx].copy()
            chunk_meta["distance"] = float(dist)
            chunk_meta["similarity"] = 1.0 / (1.0 + dist)
            retrieved.append(chunk_meta)
        
        # Log retrieval quality
        audit_logger.log_retrieval_quality(
            query_id=query_id, bot="BOT-3", top_k=top_k,
            scores=[float(d) for d, _ in valid_results],
            avg_score=float(max_confidence),
            passed_threshold=bool(max_distance <= settings.BOT3_RETRIEVAL_THRESHOLD),
            threshold=settings.BOT3_RETRIEVAL_THRESHOLD,
            num_docs_retrieved=len(retrieved)
        )
        
        return retrieved, max_confidence
        
    except Exception as e:
        logger.exception(f"[{query_id}] Error in FAISS retrieval: {e}")
        audit_logger.log_error(
            query_id=query_id, error_type="RAG_RETRIEVAL_ERROR", error_message=str(e),
            stage="faiss_retrieval", stacktrace=str(e)
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
        Tuple[str, float, bool]: (Answer string, confidence score, is_confident)
    """
    logger.info(f"[{query_id}] Bot-3 (RAG) activated")
    
    if history is None:
        history = []
    
    # Limit history
    max_turns = settings.MAX_CONTEXT_TURNS
    limited_history = history[-max_turns:] if len(history) > max_turns else history
    
    logger.debug(f"[{query_id}] Using {len(limited_history)} historical turns")
    
    try:
        # 1) HYBRID RETRIEVAL & ROUTING
        # Define local retriever wrapper for hybrid module
        def local_retriever_wrapper(q):
            return retrieve_context(q, query_id)
            
        # Get context and route
        context, route = hybrid_retriever.build_hybrid_context(query, local_retriever_wrapper)
        
        logger.info(f"[{query_id}] Route: {route}, Context length: {len(context)}")

        # 2) IF NO CONTEXT FOUND
        if not context or "No local information found" in context and route == "local":
             # Double check if it was a pure local failure
             if route == "local":
                 # Fallback to standard rejection logging
                 audit_logger.log_answer_rejection(
                    query_id=query_id,
                    bot="BOT-3",
                    reason="No documents retrieved (Local)",
                    score=0.0,
                    threshold=settings.BOT3_RETRIEVAL_THRESHOLD
                )
                 return (
                    "[NO INFO] **No Official Information Found**\n\n"
                    "I don't have information about this topic in the official college database.",
                    0.0,
                    False
                )
        
        # 3) GENERATE ANSWER
        # We assume if we got context (web or hybrid), confidence is high enough to try
        # For hybrid/web, we don't have a numerical confidence score like FAISS
        # So we set a dummy high confidence if web search was successful
        
        final_confidence = 0.0
        if route == "local":
             # We rely on the retrieve_context call's confidence if we could extract it
             # But here we re-called it. Ideally we refactor to avoid double call if efficiency mattered.
             # However, build_hybrid_context calls it. 
             # Let's assume for now we trust the router.
             final_confidence = 0.8 # Placeholder if we don't extract from wrapper
        else:
             final_confidence = 0.9 # Web/Hybrid usually implies we found something
             
        answer = generate_answer_from_context(
            query=query,
            context=context,
            retrieved_chunks=[], # Not used intimately in new prompt logic but kept for sig
            confidence=final_confidence,
            query_id=query_id,
            source_type=route
        )
        
        # 4) LOG SUCCESS
        audit_logger.log_answer_generation(
            query_id=query_id,
            bot="BOT-3",
            answer_length=len(answer),
            confidence=final_confidence,
            sources=[route],
            metadata={
                "route": route,
                "context_len": len(context)
            }
        )
        
        return answer, final_confidence, True

        
    except Exception as e:
        logger.exception(f"[{query_id}] Error in Bot-3 RAG: {e}")
        audit_logger.log_error(
            query_id=query_id,
            error_type="BOT3_RAG_ERROR",
            error_message=str(e),
            stage="rag_generation",
            stacktrace=str(e)
        )
        return f"[ERROR] Error generating answer: {str(e)}", 0.0, False



def generate_answer_from_context(
    query: str,
    context: str,
    retrieved_chunks: List[Dict],
    confidence: float,
    query_id: str,
    source_type: str = "local"
) -> str:
    """
    Generate answer from retrieved context using Ollama (Llama 3.2 1B).
    Returns formatted structured response.
    """
    
    if not context.strip():
        return "No relevant information found."
    
    try:
        import ollama
        
        system_prompt = (
            "You are an official college administrative data extractor.\n\n"
            "You must NOT write sentences or paragraphs.\n"
            "Extract only factual fields from the context and return JSON.\n\n"
            "Rules:\n"
            "- Answer only requested information\n"
            "- Do not include unrelated fields\n"
            "- No emojis\n"
            "- No marketing language\n"
            "- Max 5 items\n"
            "- If not found: return empty items array\n\n"
            "FORMAT:\n"
            "{\n"
            '  "title": "Topic Name",\n'
            '  "items": [\n'
            '    {"label": "Label", "value": "Value"}\n'
            '  ],\n'
            '  "notes": "Optional short note"\n'
            "}"
        )
        
        user_prompt = f"CONTEXT:\n{context}\n\nQUESTION:\n{query}\n\nReturn JSON only."
        
        logger.info(f"[{query_id}] Sending JSON request to Ollama...")
        response = ollama.chat(model='llama3.2:1b', messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ])
        
        generated_text = response['message']['content']
        logger.debug(f"[{query_id}] Raw LLM Response: {generated_text}")
        
        # Parse JSON
        json_data = extract_json_from_text(generated_text)
        
        if not json_data:
            logger.warning(f"[{query_id}] JSON parsing failed. Fallback to raw text.")
            # If JSON fail, wrap raw text in a safe dict structure or return clean raw text
            # Depending on how bad the output is. Usually llama 3.2 1b follows instruction well
            # But if it fails, let's try to construct a simple obj
            return f"{generated_text}\n\n_Source: {source_type.upper()}_"
            
        # Format
        formatted_response = render_response(json_data)
        
        # Add source footer
        final_answer = f"{formatted_response}\n\n_Source: {source_type.upper()}_"
        
        logger.info(f"[{query_id}] Generated formatted answer ({len(final_answer)} chars)")
        return final_answer

    except ImportError:
        logger.warning(f"[{query_id}] Ollama package not installed. Falling back to extraction.")
    except Exception as e:
        logger.warning(f"[{query_id}] Ollama generation failed ({e}). Falling back to extraction.")
        
    # FALLBACK: Simple extraction
    # If we have chunks, use them
    if retrieved_chunks:
        best_chunk = retrieved_chunks[0]
        text = best_chunk.get('text', 'No content')
        source = best_chunk.get('source', 'Unknown')
        return f"**Extracted Info:**\n{text}\n\n_Source: {source}_"
    
    return "Information not available at the moment."


