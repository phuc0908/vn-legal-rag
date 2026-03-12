# Vietnamese Legal RAG Backend

A FastAPI-based backend for Vietnamese legal document retrieval and question answering using Retrieval Augmented Generation (RAG) with Large Language Models.

## Features

- **RAG Pipeline**: Retrieve relevant legal documents and generate contextual answers
- **LLM Integration**: Support for OpenAI, Anthropic, and other LLM providers
- **Vector Store**: Uses Chroma/Pinecone for semantic document storage
- **Legal Domain**: Specialized for Vietnamese legal documents
- **FastAPI**: Modern async Python web framework
- **Configurable**: Easy to adjust LLM models, chunk sizes, and retrieval parameters

## Project Structure

```
backend/
├── app/
│   ├── api/           # API routes and endpoints
│   ├── core/          # Configuration and settings
│   ├── models/        # Pydantic schemas/models
│   ├── rag/           # RAG system (retrieval, LLM, pipeline)
│   ├── utils/         # Utility functions
│   └── __init__.py
├── tests/             # Unit and integration tests
├── data/              # Legal documents storage
├── main.py            # Entry point
├── requirements.txt   # Python dependencies
├── pyproject.toml     # Poetry configuration
├── .env.example       # Environment variables template
└── README.md
```

## Installation

1. **Clone the repository**
```bash
git clone <repo-url>
cd backend
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment variables**
```bash
cp .env.example .env
# Edit .env with your API keys and settings
```

## Configuration

### Key Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key
- `LLM_MODEL`: LLM model to use (default: gpt-4)
- `VECTOR_STORE_TYPE`: Vector store type (chroma, pinecone)
- `CHUNK_SIZE`: Document chunk size (default: 1024)
- `TOP_K_RETRIEVAL`: Number of documents to retrieve (default: 5)

## Running the Server

```bash
python main.py
```

Server will start at `http://localhost:8000`

### API Endpoints

- `GET /` - Root endpoint
- `GET /api/health` - Health check
- `POST /api/query` - Query the RAG system
- `POST /api/documents/add` - Add a document to knowledge base

## API Usage Examples

### Query Endpoint

```bash
curl -X POST "http://localhost:8000/api/query" \
  -H "Content-Type: application/json" \
  -d {
    "query": "Luật giao thông có quy định gì về tốc độ tối đa?",
    "top_k": 5
  }
```

### Response Format

```json
{
  "query": "Luật giao thông có quy định gì về tốc độ tối đa?",
  "answer": "Luật giao thông Việt Nam quy định...",
  "sources": [
    {
      "title": "Luật Giao thông Đường bộ",
      "content": "...",
      "relevance_score": 0.95,
      "metadata": {...}
    }
  ],
  "processing_time": 2.5,
  "model_used": "OpenAILLM"
}
```

## Testing

```bash
pytest tests/
```

## Development

### Code Formatting
```bash
black app/ main.py
```

### Linting
```bash
flake8 app/ main.py
```

### Type Checking
```bash
mypy app/ main.py
```

## Architecture Overview

1. **Retrieval**: Documents are embedded using sentence transformers and stored in vector database
2. **Generation**: Retrieved context is passed to LLM with a tailored prompt
3. **Pipeline**: QueryRequest → Retrieval → LLM Generation → QueryResponse

## Document Management

To add legal documents to the knowledge base:

```bash
curl -X POST "http://localhost:8000/api/documents/add" \
  -H "Content-Type: application/json" \
  -d {
    "title": "Luật Giao thông Đường bộ",
    "content": "Nội dung luật...",
    "metadata": {"type": "law", "year": 2023}
  }
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT
