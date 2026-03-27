# Backend Diagrams — VN Legal RAG

---

## 1. Auth Flow

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant AuthModule
    participant MySQL

    Client->>FastAPI: POST /api/auth/register {username, password, email}
    FastAPI->>AuthModule: get_password_hash(password)
    Note over AuthModule: passlib[bcrypt]
    AuthModule-->>FastAPI: hashed_password
    FastAPI->>MySQL: INSERT INTO users
    MySQL-->>FastAPI: user_id
    FastAPI-->>Client: UserOut {id, username, email}

    Client->>FastAPI: POST /api/auth/login {username, password}
    FastAPI->>MySQL: SELECT * FROM users WHERE username=?
    FastAPI->>AuthModule: verify_password(plain, hashed)
    Note over AuthModule: bcrypt verify
    AuthModule->>AuthModule: create_access_token(sub=username)
    Note over AuthModule: python-jose, HS256<br/>expires: 24h
    AuthModule-->>FastAPI: JWT token
    FastAPI-->>Client: {access_token, token_type: "bearer"}

    Client->>FastAPI: GET /api/auth/me (Bearer token)
    FastAPI->>AuthModule: get_current_user(token)
    AuthModule->>AuthModule: jwt.decode(token, SECRET_KEY)
    AuthModule->>MySQL: SELECT user WHERE username=sub
    MySQL-->>AuthModule: user
    AuthModule-->>FastAPI: current_user
    FastAPI-->>Client: UserOut
```

**Tech stack Auth:**

| Thành phần | Công nghệ |
|---|---|
| Framework | FastAPI |
| JWT | `python-jose` (HS256) |
| Hash mật khẩu | `passlib[bcrypt]` |
| OAuth2 scheme | `fastapi.security.OAuth2PasswordBearer` |
| Database | MySQL (PyMySQL) |
| Validation | Pydantic v2 |

---

## 2. Embedding Pipeline

```mermaid
flowchart TD
    A[MySQL — bảng pddieu] -->|"JOIN pdchude, pddemuc, pdchuong, pdtable"| B[Fetch raw data]
    B --> C["Assemble content<br/>Chủ đề + Đề mục + Chương + Nội dung"]
    C --> D{Loại dữ liệu?}

    D -->|"MySQL pddieu<br/>mỗi row = 1 Điều luật<br/>đã chia sẵn theo cấu trúc"| E["Pre-chunked = YES<br/>add_documents_direct<br/>batch = 200 rows"]

    D -->|"Raw text dài<br/>vd: file .docx upload<br/>chưa biết cách chia"| F["Pre-chunked = NO<br/>RecursiveCharacterTextSplitter<br/>chunk_size=1024 / chunk_overlap=256"]

    E --> G["HuggingFaceEmbeddings<br/>AITeamVN/Vietnamese_Embedding<br/>dim = 768"]
    F --> G
    G -->|768-dim vectors| H["ChromaDB<br/>persist: ./chroma_db/"]
    H --> I["Metadata: id_vb, chu_de_id,<br/>de_muc, loai_vb, co_quan, vbqppl"]
```

**Tech stack Embedding:**

| Thành phần | Công nghệ |
|---|---|
| Embedding model | `AITeamVN/Vietnamese_Embedding` (768 dim) |
| Framework embedding | `sentence-transformers` + `langchain-community.HuggingFaceEmbeddings` |
| Text splitter | `langchain-text-splitters.RecursiveCharacterTextSplitter` |
| Vector store | `chromadb` (Chroma, local persistent) |
| Data source | MySQL via PyMySQL |

---

## 3. RAG Pipeline

```mermaid
flowchart TD
    A["QueryRequest<br/>query + chu_de_id + top_k"] --> B

    subgraph S1 [Stage 1 — Query Rewriting]
        B["GeminiLLM.rewrite_query<br/>temperature=0.1 / max_tokens=128"] --> C["Normalized legal query<br/>(thuật ngữ pháp lý chính thức)"]
    end

    subgraph S2 [Stage 2 — Retrieval]
        C --> D["RAGSystem.retrieve<br/>top_k = 5"]
        D --> E["Encode query → 768-dim vector<br/>AITeamVN/Vietnamese_Embedding"]
        E --> F["ChromaDB similarity_search<br/>filter: chu_de_id nếu có"]
        F --> G["Top-5 docs + similarity scores"]
    end

    subgraph S3 [Stage 3 — Context Formatting]
        G --> H["_format_context<br/>Nguồn 1/2/3 + meta + content"]
    end

    subgraph S4 [Stage 4 — Generation]
        H --> I["GeminiLLM.generate_with_context<br/>gemini-3-flash-preview<br/>temperature=0.5 / max_tokens=2048"]
        I --> J["Structured answer<br/>Markdown + trích dẫn nguồn"]
    end

    J --> K["QueryResponse<br/>answer + sources + processing_time"]
    K -->|có conversation_id| L["Lưu MySQL<br/>role: user / assistant"]
    K --> M[Client]
```

**Tech stack RAG:**

| Stage | Công nghệ |
|---|---|
| Query rewriting | `google-genai` Gemini 3 Flash Preview |
| Embedding query | `AITeamVN/Vietnamese_Embedding` (sentence-transformers) |
| Vector retrieval | ChromaDB (`similarity_search_with_relevance_scores`) |
| Context formatting | Python string templating |
| Generation | `google-genai` Gemini `gemini-3-flash-preview` (temp=0.5) |
| Conversation history | MySQL (bảng `conversations` + `messages`) |
| API | FastAPI async |

---

## 4. ERD — Toàn bộ Database

```mermaid
erDiagram
    pdchude {
        VARCHAR id PK
        TEXT ten
        INT stt
    }

    pddemuc {
        VARCHAR id PK
        TEXT ten
        INT stt
        VARCHAR chude_id FK
    }

    pdchuong {
        VARCHAR mapc PK
        TEXT ten
        TEXT chimuc
        INT stt
        VARCHAR demuc_id FK
    }

    pddieu {
        VARCHAR mapc PK
        TEXT ten
        INT chimuc
        INT stt
        TEXT noidung
        TEXT vbqppl
        TEXT vbqppl_link
        VARCHAR demuc_id FK
        VARCHAR chuong_id FK
        VARCHAR chude_id FK
    }

    pdtable {
        INT id PK
        VARCHAR dieu_id FK
        TEXT html
    }

    pdfile {
        INT id PK
        VARCHAR dieu_id FK
        TEXT link
        TEXT path
    }

    pdmuclienquan {
        INT id PK
        VARCHAR dieu_id1_id FK
        VARCHAR dieu_id2_id FK
    }

    vbpl {
        INT id PK
        TEXT noidung
    }

    vb_chimuc {
        INT id PK
        INT id_vb FK
        TEXT noi_dung
        INT chi_muc_cha
    }

    users {
        INT id PK
        VARCHAR username
        VARCHAR email
        VARCHAR hashed_password
        VARCHAR full_name
        BOOLEAN is_active
        TIMESTAMP created_at
    }

    conversations {
        VARCHAR id PK
        INT user_id FK
        VARCHAR title
        TIMESTAMP created_at
    }

    messages {
        INT id PK
        VARCHAR conversation_id FK
        VARCHAR role
        TEXT content
        TIMESTAMP created_at
    }

    pdchude ||--o{ pddemuc : "có nhiều"
    pddemuc ||--o{ pdchuong : "có nhiều"
    pddemuc ||--o{ pddieu : "thuộc"
    pdchuong ||--o{ pddieu : "có nhiều"
    pdchude ||--o{ pddieu : "thuộc"
    pddieu ||--o{ pdtable : "có bảng"
    pddieu ||--o{ pdfile : "có file"
    pddieu ||--o{ pdmuclienquan : "liên quan tới"
    vbpl ||--o{ vb_chimuc : "được index"
    users ||--o{ conversations : "có"
    conversations ||--o{ messages : "chứa"
```

---

## 5. Sơ đồ phân nhóm CSDL theo chức năng

```mermaid
flowchart LR
    subgraph PD ["Pháp Điển — Nội dung pháp luật"]
        A[pdchude<br/>Chủ đề] --> B[pddemuc<br/>Đề mục]
        B --> C[pdchuong<br/>Chương]
        C --> D[pddieu<br/>Điều luật]
        D --> E[pdtable<br/>Bảng HTML]
        D --> F[pdfile<br/>File đính kèm]
        D <-->|tham chiếu chéo| G[pdmuclienquan<br/>Điều liên quan]
    end

    subgraph VB ["Văn bản pháp luật — Legacy"]
        H[vbpl<br/>Văn bản] --> I[vb_chimuc<br/>Chỉ mục]
    end

    subgraph APP ["Ứng dụng — User & Chat"]
        J[users<br/>Tài khoản] --> K[conversations<br/>Hội thoại]
        K --> L[messages<br/>Tin nhắn]
    end

    subgraph VEC ["Vector Store — ChromaDB"]
        M["ChromaDB<br/>./chroma_db/<br/>768-dim vectors"]
    end

    D -->|"ingest: noidung + metadata<br/>JOIN pdchude, pddemuc, pdchuong"| M
    I -->|"ingest legacy<br/>scripts/ingest_from_db.py"| M
    M -->|"similarity search"| N[RAG Pipeline]
    L -->|"lưu lịch sử"| N
```

---

## 6. Cấu trúc phân cấp Pháp Điển

```mermaid
flowchart TD
    A["pdchude<br/>Chủ đề<br/>vd: Hôn nhân và Gia đình"] --> B
    B["pddemuc<br/>Đề mục<br/>vd: Luật Hôn nhân 2014"] --> C
    C["pdchuong<br/>Chương<br/>vd: Chương I — Quy định chung"] --> D
    D["pddieu — CHÍNH<br/>Điều luật<br/>vd: Điều 3. Giải thích từ ngữ"]
    D --> E["pdtable<br/>Bảng HTML đính kèm"]
    D --> F["pdfile<br/>File đính kèm"]
    D <-->|"liên kết chéo"| G["pdmuclienquan<br/>Điều liên quan"]
```

---

## 7. Tổng quan toàn hệ thống

```mermaid
flowchart TD
    Client["CLIENT\nMobile / Web"] -->|JWT Bearer| Auth
    Client -->|POST /api/query| RAG

    subgraph Auth ["Auth Layer"]
        A1["FastAPI + JWT\nbcrypt + MySQL"]
    end

    subgraph RAG ["RAG Pipeline"]
        R1["Rewrite Query\nGemini Flash"]
        R2["Retrieve\nChromaDB + Embeddings"]
        R3["Generate\nGemini Flash"]
        R1 --> R2 --> R3
    end

    R2 <-->|"similarity search"| VEC["ChromaDB\n768-dim vectors"]
    VEC <-->|"indexed from"| DB_PD["MySQL\npddieu hierarchy"]
    R3 <-->|"save history"| DB_APP["MySQL\nusers / conversations / messages"]
    Auth <-->|"validate user"| DB_APP
```

---

## Bảng tóm tắt CSDL

| Nhóm | Bảng | Vai trò |
|---|---|---|
| **Pháp Điển** | `pdchude` | Chủ đề pháp luật (level 1) |
| | `pddemuc` | Đề mục / Bộ luật (level 2) |
| | `pdchuong` | Chương (level 3) |
| | `pddieu` | **Điều luật — bảng chính, nguồn cho vector** |
| | `pdtable` | Bảng HTML trong điều |
| | `pdfile` | File đính kèm |
| | `pdmuclienquan` | Quan hệ tham chiếu chéo giữa các điều |
| **Văn bản (Legacy)** | `vbpl` | Toàn văn văn bản pháp luật |
| | `vb_chimuc` | Index theo chương/điều (embed cũ) |
| **Ứng dụng** | `users` | Tài khoản người dùng |
| | `conversations` | Phiên hội thoại (UUID) |
| | `messages` | Tin nhắn user/assistant |
| **Vector Store** | ChromaDB | Lưu trữ embedding từ `pddieu` |
