# Frontend — VN Legal RAG

Giao diện hỏi đáp pháp luật Việt Nam, kiểu ChatGPT.

## Công nghệ

| Thành phần | Chi tiết |
|-----------|---------|
| Framework | React 18 + Vite |
| State | Zustand |
| HTTP | Axios |
| Markdown | react-markdown |
| Style | CSS3 |

## Cấu trúc thư mục

```
frontend/src/
├── components/
│   ├── Sidebar.jsx         # Danh sách hội thoại, user info, logout
│   ├── ChatWindow.jsx      # Khu vực hiển thị messages
│   ├── MessageItem.jsx     # Render từng message (markdown + sources)
│   └── InputArea.jsx       # Ô nhập câu hỏi + dropdown chọn chủ đề
├── pages/
│   └── ChatPage.jsx        # Trang chat chính
├── services/
│   └── api.js              # Axios calls đến backend
├── store/
│   └── chatStore.js        # Zustand store (conversations, messages)
├── styles/                 # CSS files
├── App.jsx
└── main.jsx
```

## Cài đặt

```bash
npm install
```

## Cấu hình `.env`

```env
VITE_API_URL=http://localhost:8000
```

## Chạy

```bash
npm run dev      # Development (http://localhost:3000)
npm run build    # Build production
npm run preview  # Preview bản build
npm run lint     # Kiểm tra lint
```

## Tích hợp API

Backend proxy qua Vite dev server (`/api` → `http://localhost:8000/api`).

| Endpoint | Mô tả |
|----------|-------|
| `POST /api/auth/login` | Đăng nhập |
| `POST /api/auth/register` | Đăng ký |
| `GET /api/auth/me` | Thông tin user |
| `POST /api/query` | Gửi câu hỏi (hỗ trợ `chu_de_id` filter) |
| `GET /api/conversations` | Lấy danh sách hội thoại |
| `POST /api/conversations` | Tạo hội thoại mới |
| `DELETE /api/conversations/{id}` | Xóa hội thoại |
| `GET /api/law/chude` | Danh sách chủ đề (dùng cho dropdown) |

## Tính năng

- Đăng ký / đăng nhập tài khoản
- Giao diện chat kiểu ChatGPT
- Lịch sử hội thoại (sidebar)
- **Chọn chủ đề** để lọc vector trước khi hỏi (45 chủ đề pháp điển)
- Trích dẫn nguồn văn bản pháp luật
- Render Markdown trong câu trả lời
- Xóa hội thoại
