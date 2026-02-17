# Hybrid RAG Implementation Guide

This module implements a Hybrid RAG system that dynamically routes user queries to:
1.  **Local Knowledge Base (FAISS)** for college-specific queries.
2.  **Web Search (Tavily)** for current events and general knowledge.
3.  **Hybrid Mode** for comparisons or queries requiring both.

## Capabilities

- **Strict Context Adherence**: The generator (Ollama) is instructed to answer *only* from retrieved context.
- **Caching**: Web search results are cached for 1 hour to improve performance and reduce API usage.
- **Transparency**: Every answer includes its source type (LOCAL, WEB, HYBRID) and specific source references.

## Setup

1.  **Install Dependencies**:
    ```bash
    pip install tavily-python langchain-community beautifulsoup4
    ```

2.  **Configure API Key**:
    Add your Tavily API Key to your environment variables or `.env` file:
    ```
    TAVILY_API_KEY=tvly-xxxxxxxxxxxx
    ```
    Or edit `college_chatbot/config/settings.py`.

## Example Queries (Routing Logic)

| Query | Route | Reasoning |
| :--- | :--- | :--- |
| "What is the tuition fee for CSE?" | **LOCAL** | Contains "fee", "tuition" (Local Keywords) |
| "Who is part of the faculty in ECE?" | **LOCAL** | Contains "faculty" (Local Keyword) |
| "What are the latest AI trends?" | **WEB** | Contains "latest", "trends", "AI" (Web Keywords) |
| "Current technology news in India" | **WEB** | Contains "news", "technology", "India" (Web Keywords) |
| "Compare our college placements with IIT Hyderabad" | **HYBRID** | Contains "compare", "college" (Hybrid + Local Keywords) |
| "Difference between RVR placement and national average" | **HYBRID** | Contains "difference", "placement", "national" |

## Architecture

- **`college_chatbot/bots/hybrid_retriever.py`**: Core logic for routing and web search.
- **`college_chatbot/bots/bot3_rag.py`**: Integrated the hybrid retriever into the existing RAG pipeline.
- **`college_chatbot/config/settings.py`**: Configuration for API keys and cache settings.

## Testing

Run the included test script to verify routing logic:
```bash
python college_chatbot/test_hybrid.py
```
