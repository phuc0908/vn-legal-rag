# VN Legal RAG

Ứng dụng hỏi đáp pháp luật Việt Nam sử dụng kỹ thuật RAG (Retrieval-Augmented Generation).

## Kiến trúc

```
vn-legal-rag/
├── backend/     # FastAPI + RAG pipeline
└── frontend/    # React + Vite
```

| Thành phần | Công nghệ |
|-----------|-----------|
| Backend | FastAPI, LangChain, ChromaDB, Google Gemini |
| Frontend | React 18, Vite, Zustand, Axios |
| Database | MySQL (pháp điển + văn bản pháp luật) |
| Embedding | `hiieu/halong_embedding` (Sentence Transformers) |
| Vector Store | ChromaDB |

## Luồng hoạt động

```
Câu hỏi người dùng
    → Embedding câu hỏi
    → Tìm văn bản liên quan trong ChromaDB (nguồn: vb_chimuc)
    → Ghép context → Gemini sinh câu trả lời
    → Trả về kết quả có trích dẫn nguồn
```

## Cài đặt nhanh

### Yêu cầu
- Python 3.10+
- Node.js 18+
- MySQL đang chạy với database `law`

### 1. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/macOS

pip install -r requirements.txt
cp .env.example .env           # Điền GEMINI_API_KEY và thông tin DB
python scripts/setup_db.py     # Tạo bảng users, conversations, messages
python scripts/ingest_from_db.py --reset  # Index vb_chimuc → ChromaDB
python main.py
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

| Service | URL |
|---------|-----|
| Backend API | http://localhost:8000 |
| Frontend | http://localhost:3000 |
| Swagger UI | http://localhost:8000/docs |

## Tài liệu chi tiết

- [Backend README](backend/README.md)
- [Frontend README](frontend/README.md)
- [Cấu trúc Database](backend/DATABASE.md)
