# Backend — VN Legal RAG

FastAPI backend cho hệ thống hỏi đáp pháp luật Việt Nam sử dụng RAG.

## Công nghệ

| Thành phần | Chi tiết |
|-----------|---------|
| Framework | FastAPI |
| LLM | Google Gemini (`gemini-3-flash-preview`) |
| Embedding | `AITeamVN/Vietnamese_Embedding` (Sentence Transformers) |
| Vector Store | ChromaDB |
| Database | MySQL (PyMySQL) |
| Auth | JWT (python-jose + bcrypt) |
| RAG | LangChain + ChromaDB |

## Cấu trúc thư mục

```
backend/
├── main.py                     # Entry point FastAPI
├── requirements.txt
├── .env                        # Cấu hình (không commit)
├── chroma_db/                  # Dữ liệu vector (auto tạo khi ingest)
│
├── app/
│   ├── api/
│   │   ├── routes.py           # POST /query, GET /health
│   │   ├── auth_routes.py      # POST /auth/register, /auth/login, GET /auth/me
│   │   ├── conversation_routes.py  # CRUD conversations & messages
│   │   ├── law_routes.py       # Duyệt pháp điển (chủ đề, điều, tìm kiếm)
│   │   └── dependencies.py     # get_current_user dependency
│   ├── core/
│   │   ├── config.py           # Settings (pydantic-settings)
│   │   └── auth.py             # JWT, bcrypt utilities
│   ├── db/
│   │   └── database.py         # MySQL connection, query_one, query_all
│   ├── models/
│   │   └── schemas.py          # Pydantic request/response schemas
│   ├── rag/
│   │   ├── pipeline.py         # RAGPipeline: retrieval + generation
│   │   ├── retrieval.py        # ChromaVectorStore, RAGSystem
│   │   └── llm.py              # GeminiLLM, LLMManager, PROMPT_TEMPLATE
│   └── utils/
│       ├── helpers.py
│       └── db_helpers.py       # save_message, update_conversation_title
│
└── scripts/
    ├── setup_db.py             # Tạo bảng users/conversations/messages
    ├── ingest_from_pddieu.py   # Index pddieu → ChromaDB (script chính)
    ├── ingest_from_db.py       # Index vb_chimuc → ChromaDB (legacy)
    ├── ingest_legal_docx.py    # Index từ file .docx (legacy)
    ├── migrate.py
    └── test_query.py
```

## Cài đặt

```bash
python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt
```

## Cấu hình `.env`

```env
# LLM
GEMINI_API_KEY=your_key_here
LLM_MODEL=gemini-3-flash-preview

# Database
DB_HOST=localhost
DB_PORT=3307
DB_USER=root
DB_PASSWORD=your_password
DB_NAME=law

# Security
SECRET_KEY=your_random_secret_key

# RAG
SIMILARITY_THRESHOLD=0.5
TOP_K_RETRIEVAL=5
```

## Khởi chạy lần đầu

```bash
# 1. Tạo bảng users, conversations, messages
python scripts/setup_db.py

# 2. Preview dữ liệu trước khi ingest (tuỳ chọn)
python scripts/ingest_from_pddieu.py --preview-only

# 3. Index toàn bộ pddieu vào ChromaDB
#    --reset: xóa ChromaDB cũ trước khi ingest
python scripts/ingest_from_pddieu.py --reset

# 4. Chạy server
python main.py
```

> Server chạy tại http://localhost:8000
> Swagger UI: http://localhost:8000/docs

## Nguồn dữ liệu vector

Script `ingest_from_pddieu.py` đọc bảng `pddieu` và JOIN sang các bảng liên quan:

| Bảng | Quan hệ | Dữ liệu lấy |
|------|---------|-------------|
| `pddieu` | Bảng chính | Nội dung điều luật |
| `pdchude` | `pddieu.chude_id` | Tên chủ đề (`chu_de_id` dùng làm filter) |
| `pddemuc` | `pddieu.demuc_id` | Tên đề mục |
| `pdchuong` | `pddieu.chuong_id` | Tên chương |
| `pdtable` | `pddieu.mapc` | Bảng dữ liệu đính kèm |

Mỗi row `pddieu` = 1 vector trong ChromaDB. Metadata vector gồm: `chu_de_id`, `chu_de`, `de_muc`, `chuong_ten`, `dieu_mapc`, `vbqppl`.

### Lọc theo chủ đề

Khi người dùng chọn chủ đề trong giao diện, query sẽ filter ChromaDB:
```python
filter_where = {"chu_de_id": "3"}  # chỉ tìm trong chủ đề id=3
```

### Tuỳ chọn CLI

```bash
python scripts/ingest_from_pddieu.py --preview-only        # Xem trước, không ingest
python scripts/ingest_from_pddieu.py --reset               # Xóa ChromaDB và ingest lại
python scripts/ingest_from_pddieu.py --chude-id 3          # Chỉ ingest chủ đề id=3
```

## Re-index

```bash
python scripts/ingest_from_pddieu.py --reset
```

## API Endpoints

### Auth
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/api/auth/register` | Đăng ký tài khoản |
| POST | `/api/auth/login` | Đăng nhập, nhận JWT |
| GET | `/api/auth/me` | Thông tin user hiện tại |

### RAG
| Method | Endpoint | Mô tả | Auth |
|--------|----------|-------|------|
| POST | `/api/query` | Hỏi đáp pháp luật (hỗ trợ `chu_de_id` filter) | Có |
| GET | `/api/health` | Kiểm tra trạng thái hệ thống | Không |

### Conversations
| Method | Endpoint | Mô tả | Auth |
|--------|----------|-------|------|
| GET | `/api/conversations` | Danh sách hội thoại | Có |
| POST | `/api/conversations` | Tạo hội thoại mới | Có |
| GET | `/api/conversations/{id}` | Chi tiết + messages | Có |
| DELETE | `/api/conversations/{id}` | Xóa hội thoại | Có |

### Pháp điển (không cần auth)
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/law/stats` | Thống kê số lượng điều/chương |
| GET | `/api/law/chude` | Danh sách chủ đề |
| GET | `/api/law/demuc?chude_id=` | Đề mục theo chủ đề |
| GET | `/api/law/chuong?demuc_id=` | Chương theo đề mục |
| GET | `/api/law/dieu/list?chuong_id=` | Điều theo chương |
| GET | `/api/law/dieu/{mapc}` | Nội dung đầy đủ một điều |
| GET | `/api/law/search?q=` | Tìm kiếm điều theo từ khóa |

## Ví dụ query với filter chủ đề

```bash
curl -X POST http://localhost:8000/api/query \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"query": "Thủ tục ly hôn?", "top_k": 5, "chu_de_id": "3"}'
```
