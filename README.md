# Vietnamese Legal RAG

A complete web application for Vietnamese legal document retrieval and question answering using React frontend and Python RAG backend.

## Project Structure

### Frontend (`/frontend`)
- **Framework**: React 18 with Vite
- **Styling**: CSS with ChatGPT-like interface
- **State Management**: Zustand
- **HTTP Client**: Axios
- **Features**:
  - ChatGPT-like conversation interface
  - Document source citations
  - Conversation history management
  - Real-time typing indicators
  - Responsive design

### Backend (`/backend`)
- **Framework**: FastAPI
- **RAG System**: LangChain
- **Vector Store**: Chroma/Pinecone
- **LLM**: OpenAI/Anthropic
- **Embeddings**: Sentence Transformers
- **Features**:
  - Retrieval Augmented Generation (RAG)
  - Legal document knowledge base
  - Async API endpoints
  - Configurable LLM providers
  - Vector similarity search

## Quick Start

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Access at `http://localhost:3000`

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
python main.py
```

Access at `http://localhost:8000`

## API Specification

### Query Endpoint

**POST** `/api/query`

Request:
```json
{
  "query": "Câu hỏi pháp lý?",
  "top_k": 5,
  "conversation_id": "optional"
}
```

Response:
```json
{
  "query": "Câu hỏi pháp lý?",
  "answer": "Trả lời chi tiết...",
  "sources": [
    {
      "title": "Tên tài liệu",
      "content": "Nội dung trích dẫn",
      "relevance_score": 0.95,
      "metadata": {...}
    }
  ],
  "processing_time": 2.5
}
```

### Health Check

**GET** `/api/health`

Response:
```json
{
  "status": "ok",
  "version": "1.0.0",
  "llm_configured": true,
  "vector_store_ready": true
}
```

## Configuration

### Backend Environment Variables

```env
# LLM
OPENAI_API_KEY=your_key
LLM_MODEL=gpt-4
LLM_TEMPERATURE=0.7

# RAG
CHUNK_SIZE=1024
CHUNK_OVERLAP=256
TOP_K_RETRIEVAL=5

# Vector Store
VECTOR_STORE_TYPE=chroma
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

### Frontend Environment Variables

```env
REACT_APP_API_URL=http://localhost:8000/api
```

## Features

### Frontend
- ✅ ChatGPT-like conversation interface
- ✅ Conversation history with ability to switch between chats
- ✅ Display of source documents with citations
- ✅ Real-time message streaming
- ✅ Responsive design for mobile and desktop
- ✅ Markdown support for formatted answers

### Backend
- ✅ RAG pipeline with document retrieval
- ✅ LLM-powered answer generation
- ✅ Vector similarity search
- ✅ Document management API
- ✅ Configurable parameters
- ✅ Multiple LLM provider support

## Development

### Frontend Scripts
```bash
npm run dev      # Development server
npm run build    # Production build
npm run preview  # Preview build
npm run lint     # Linting
```

### Backend Commands
```bash
python main.py           # Start server
pytest tests/           # Run tests
black app/ main.py      # Format code
flake8 app/ main.py     # Lint code
```

## Database Schema

### Documents
- title: String
- content: Text
- metadata: JSON
- embedding: Vector
- created_at: DateTime

### Conversations
- id: UUID
- user_id: UUID (optional)
- messages: Array
- created_at: DateTime
- updated_at: DateTime

## Requirements

### Frontend
- Node.js 18+
- npm or yarn

### Backend
- Python 3.10+
- pip or poetry

## Deployment

### Frontend (Vercel/Netlify)
```bash
cd frontend
npm run build
# Deploy dist/ folder
```

### Backend (Docker/Railway/Heroku)
```bash
cd backend
docker build -t vn-legal-rag .
docker run -p 8000:8000 vn-legal-rag
```

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## License

MIT License

## Support

For issues and feature requests, please open an issue on GitHub.

## Authors

- Your Name
- Contributors welcome!
