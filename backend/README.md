# Vietnamese Legal RAG Backend

FastAPI-based backend for Vietnamese legal document retrieval and question answering using RAG with LLMs.

## Features

RAG Pipeline with document retrieval and LLM answer generation, LLM Integration (OpenAI/Anthropic), Vector Store (Chroma/Pinecone), Specialized for Vietnamese legal documents, Configurable parameters and models.

## Project Structure

app/
- api/: API routes and endpoints
- core/: Configuration and settings
- models/: Pydantic schemas
- rag/: RAG system (retrieval, LLM, pipeline)
- utils/: Helper functions

tests/: Unit and integration tests
data/: Document storage
main.py: Entry point
requirements.txt: Dependencies

## Installation

1. Create virtual environment
```bash
python -m venv venv
venv\Scripts\activate
```

2. Install dependencies
```bash
pip install -r requirements.txt
```

3. Configure environment
```bash
cp .env.example .env
```

4. Run server
```bash
python main.py
```

Server at http://localhost:8000

## Configuration

Key environment variables:
- OPENAI_API_KEY: OpenAI API key
- LLM_MODEL: Model to use (default: gpt-4)
- VECTOR_STORE_TYPE: Vector store (chroma, pinecone)
- CHUNK_SIZE: Document chunk size (default: 1024)
- TOP_K_RETRIEVAL: Documents to retrieve (default: 5)

## API Endpoints

GET / - Root endpoint
GET /api/health - Health check
POST /api/query - Query the RAG system
POST /api/documents/add - Add document to knowledge base

## Query Endpoint

POST /api/query
Request: {"query": "Luật giao thông...", "top_k": 5}
Response: {"query": "...", "answer": "...", "sources": [...], "processing_time": 2.5}

## Development

Code formatting: black app/ main.py
Linting: flake8 app/ main.py
Type checking: mypy app/ main.py
Tests: pytest tests/

## Architecture

Retrieval: Documents embedded using Sentence Transformers and stored in vector database
Generation: Retrieved context passed to LLM with tailored prompt
Pipeline: QueryRequest > Retrieval > LLM Generation > QueryResponse

## License

MIT

