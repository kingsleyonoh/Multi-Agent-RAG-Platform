# Introduction to RAG Systems

Retrieval-Augmented Generation (RAG) is a technique that bridges the gap between large language models and proprietary data.
Instead of fine-tuning a model, a RAG system retrieves relevant context from a vector database prior to generating a response.

## Core Components
1. **Ingestion Pipeline**: Processes raw files (PDFs, Markdown, HTML), chunks them into smaller segments, and generates dense vector embeddings.
2. **Retrieval System**: Uses hybrid search (semantic + keyword + graph) to find the most relevant chunks.
3. **Generation**: An LLM (like GPT-4 or Claude 3) takes the retrieved context and answers the user's query while citing sources.

This platform utilizes pgvector for semantic search, Neo4j for relationship mapping, and Redis for aggressive semantic caching.
