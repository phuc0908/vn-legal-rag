# VN Legal RAG

Ứng dụng hỏi đáp pháp luật Việt Nam sử dụng kỹ thuật RAG (Retrieval-Augmented Generation).

## Demo



https://github.com/user-attachments/assets/38fa00ca-1122-48d9-9471-c360898f5b4b



## Kiến trúc

```
vn-legal-rag/
├── backend/     # FastAPI + RAG pipeline
├── frontend/    # React + Vite (web)
└── mobile/      # React Native + Expo (iOS/Android)
```

| Thành phần | Công nghệ |
|-----------|-----------|
| Backend | FastAPI, LangChain, ChromaDB, Google Gemini |
| Frontend | React 18, Vite, Zustand, Axios |
| Mobile | React Native 0.81, Expo SDK 54, React Navigation |
| Database | MySQL (pháp điển + văn bản pháp luật) |
| Embedding | `AITeamVN/Vietnamese_Embedding` (Sentence Transformers) |
| Vector Store | ChromaDB |

## Luồng hoạt động

```
Câu hỏi người dùng
    → (Tuỳ chọn) Chọn chủ đề để lọc vector theo chu_de_id
    → Embedding câu hỏi bằng AITeamVN/Vietnamese_Embedding
    → Tìm văn bản liên quan trong ChromaDB (nguồn: bảng pddieu)
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
python scripts/ingest_from_pddieu.py --reset  # Index pddieu → ChromaDB
python main.py
```

### 2. Frontend (Web)

```bash
cd frontend
npm install
npm run dev
```

### 3. Mobile (Expo Go)

```bash
cd mobile
npm install
# Sửa IP backend trong src/services/api.ts
npx expo start
```

| Service | URL |
|---------|-----|
| Backend API | http://localhost:8000 |
| Frontend | http://localhost:3000 |
| Swagger UI | http://localhost:8000/docs |

## Tài liệu chi tiết

- [Backend README](backend/README.md)
- [Frontend README](frontend/README.md)
- [Mobile README](mobile/README.md)
