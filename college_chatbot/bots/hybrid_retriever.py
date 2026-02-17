import os
import time
import logging
from typing import List, Dict, Tuple, Optional, Any
from bs4 import BeautifulSoup

# Try importing Tavily, handle gracefully if missing during setup
try:
    from tavily import TavilyClient
except ImportError:
    TavilyClient = None

from config.settings import settings
from core.logger import get_logger
from core.audit_logger import get_audit_logger

# Import ModelManager strictly for local retrieval access if needed
# local_retriever logic from bot3 will be used via callback or direct call
from core.model_manager import ModelManager

logger = get_logger("hybrid_retriever")
audit_logger = get_audit_logger("hybrid_retriever")

class HybridRetriever:
    """
    Orchestrates Hybrid RAG:
    - Route query (Local vs Web vs Hybrid)
    - Retrieve from appropriate source
    - Build combined context
    """
    
    def __init__(self):
        self.api_key = os.environ.get("TAVILY_API_KEY") or settings.TAVILY_API_KEY
        if not self.api_key:
            logger.warning("TAVILY_API_KEY not found. Web search will be disabled.")
            self.tavily = None
        elif TavilyClient:
            self.tavily = TavilyClient(api_key=self.api_key)
        else:
            logger.error("TavilyClient not imported. Install via `pip install tavily-python`.")
            self.tavily = None
            
        # Simple in-memory cache: {query: (result, timestamp)}
        self.cache = {}
        self.cache_ttl = 3600  # 1 hour in seconds

    def _clean_html(self, html_content: str) -> str:
        """Clean HTML content to plain text."""
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            # Remove scripts and styles
            for script in soup(["script", "style"]):
                script.extract()
            text = soup.get_text(separator=' ')
            # Clean whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = '\n'.join(chunk for chunk in chunks if chunk)
            return text[:4000] # Hard limit
        except Exception as e:
            logger.error(f"Error cleaning HTML: {e}")
            return html_content[:4000]

    def search_web(self, query: str) -> str:
        """
        Perform web search using Tavily API.
        Returns combined context string from top results.
        And implements caching.
        """
        # Check cache
        if query in self.cache:
            result, timestamp = self.cache[query]
            if time.time() - timestamp < self.cache_ttl:
                logger.info(f"Cache hit for web query: {query}")
                return result
            else:
                del self.cache[query]

        if not self.tavily:
            return ""

        try:
            logger.info(f"Searching web for: {query}")
            # Use search_depth="advanced" for better results if available, else standard
            response = self.tavily.search(query=query, search_depth="advanced", max_results=3)
            
            results = response.get("results", [])
            if not results:
                return ""

            combined_content = []
            for res in results:
                title = res.get("title", "No Title")
                url = res.get("url", "")
                raw_content = res.get("content", "")
                
                # If content is very short or looks like HTML, try cleaning or using raw
                # Tavily usually returns clean text in 'content', but sometimes 'raw_content' exists
                clean_text = raw_content 
                
                combined_content.append(f"Source: {title} ({url})\nContent: {clean_text}\n")

            final_context = "\n---\n".join(combined_content)
            
            # Update cache
            self.cache[query] = (final_context, time.time())
            
            return final_context

        except Exception as e:
            logger.error(f"Tavily search failed: {e}")
            return ""

    def route_query(self, query: str) -> str:
        """
        Determine if query is 'local', 'web', or 'hybrid'.
        """
        query_lower = query.lower()
        
        # Keywords
        local_keywords = [
             "college", "department", "fee", "tuition", "placement", "campus", 
             "hostel", "library", "exam", "syllabus", "faculty", "admin", 
             "laboratory", "professors", "rvr", "jc", "bus", "transport",
             "canteen", "calendar", "result"
        ]
        
        web_keywords = [
            "news", "event", "hackathon", "technology", "ai", "compare", 
            "ranking", "current affairs", "world", "india", "global", 
            "latest", "google", "microsoft", "trend", "politics", "weather"
        ]
        
        hybrid_keywords = [
            "compare", "vs", "better than", "difference between", "ranking of our college",
            "market trend", "industry demand"
        ]

        # Check hybrid first (overrides others)
        if any(k in query_lower for k in hybrid_keywords):
             # If it mentions college specifically + hybrid keyword -> Hybrid
             # If it's just "compare IIT vs NIT" -> Web
             # But "compare RVR vs IIT" -> Hybrid
             if any(lk in query_lower for lk in local_keywords) or "us" in query_lower or "our" in query_lower:
                 return "hybrid"
        
        # Check local
        is_local = any(k in query_lower for k in local_keywords)
        
        # Check web
        is_web = any(k in query_lower for k in web_keywords)
        
        if is_local and not is_web:
            return "local"
        if is_web and not is_local:
            return "web"
        if is_local and is_web:
            return "hybrid"
            
        # Default fallback (conservative -> local, or check classifier)
        # For now, default to local as it's a college bot
        return "local"

    def build_hybrid_context(self, query: str, local_retriever_func) -> Tuple[str, str]:
        """
        Orchestrates the retrieval based on routing.
        
        Args:
            query: User query
            local_retriever_func: Function to call for local retrieval (returns context str or list)
            
        Returns:
            (context_str, source_type)
        """
        route = self.route_query(query)
        logger.info(f"Query routed to: {route}")
        
        context = ""
        
        if route == "local":
            # Call provided local retriever
            # Expecting local_retriever_func to return (list_of_chunks, confidence) or similar
            # But let's assume the caller handles the specific format
            # We'll expect it to return a string or we handle it
            pass # logic below
            
        # Execute based on route
        local_context = ""
        web_context = ""
        
        if route in ["local", "hybrid"]:
            # Retrieve local
            try:
                # We need to adapt the local_retriever_func result
                # bot3's retrieve_context returns (chunks, confidence)
                chunks, conf = local_retriever_func(query)
                if chunks:
                    # Simple formatting
                    local_context = "\n\n".join([f"[Local Source: {c.get('source','Doc')}]\n{c.get('text','')}" for c in chunks])
                else:
                    local_context = "No local information found."
            except Exception as e:
                logger.error(f"Local retrieval failed: {e}")
                local_context = "Error accessing local database."

        if route in ["web", "hybrid"]:
            web_context = self.search_web(query)
            if not web_context:
                web_context = "No web information found."

        # Combine
        if route == "local":
            context = local_context
        elif route == "web":
            context = web_context
        else: # hybrid
            context = f"=== LOCAL COLLEGE KNOWLEDGE ===\n{local_context}\n\n=== WEB KNOWLEDGE ===\n{web_context}"
            
        return context, route

# Singleton instance
hybrid_retriever = HybridRetriever()
