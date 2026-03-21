# VN Legal RAG — Mobile App

Ứng dụng di động tra cứu và tư vấn pháp luật Việt Nam, được xây dựng bằng **React Native + Expo**. Kết nối với backend FastAPI của hệ thống VN Legal RAG.

---

## Tính năng

| Tab | Chức năng |
|-----|-----------|
| 🏠 Trang chủ | Tìm kiếm nhanh, danh mục lĩnh vực pháp luật, câu hỏi thường gặp |
| 🔍 Tra cứu | Tìm kiếm full-text điều luật theo từ khóa |
| 🤖 Tư vấn AI | Chat với AI, chọn chủ đề để lọc vector, lưu lịch sử hội thoại **(yêu cầu đăng nhập)** |
| 📚 Pháp điển | Duyệt phân cấp: Chủ đề → Đề mục → Chương → Điều |

> **Lưu ý:** Trang chủ, Tra cứu, Pháp điển có thể dùng không cần đăng nhập. Chỉ tab Tư vấn AI yêu cầu tài khoản.

---

## Cấu trúc thư mục

```
mobile/
├── App.tsx                        # Entry point
├── index.js                       # registerRootComponent
├── app.json                       # Expo config
├── babel.config.js
├── tsconfig.json
├── package.json
└── src/
    ├── theme/
    │   └── colors.ts              # Bảng màu toàn app
    ├── types/
    │   └── index.ts               # TypeScript interfaces & navigation types
    ├── services/
    │   └── api.ts                 # Axios client — cấu hình IP backend tại đây
    ├── store/
    │   ├── authStore.ts           # Zustand: trạng thái đăng nhập (persist AsyncStorage)
    │   └── chatStore.ts           # Zustand: danh sách hội thoại
    ├── navigation/
    │   └── AppNavigator.tsx       # Root Stack + Bottom Tabs navigator
    ├── screens/
    │   ├── LoginScreen.tsx        # Modal đăng nhập
    │   ├── RegisterScreen.tsx     # Modal đăng ký
    │   ├── HomeScreen.tsx
    │   ├── SearchScreen.tsx
    │   ├── ChatScreen.tsx         # Yêu cầu auth, hiện prompt đăng nhập nếu chưa
    │   ├── LawBrowserScreen.tsx
    │   └── DieuDetailScreen.tsx
    └── components/
        ├── MessageItem.tsx        # Bubble chat + hiển thị nguồn tham khảo
        ├── InputArea.tsx          # Ô nhập + modal chọn chủ đề
        └── ConversationDrawer.tsx # Drawer danh sách hội thoại
```

---

## Yêu cầu

- Node.js >= 18
- npm >= 9
- Expo Go SDK 54 (cài trên điện thoại)
- Backend VN Legal RAG đang chạy (cùng mạng WiFi)

---

## Cài đặt

```bash
cd mobile
npm install
```

---

## Cấu hình IP Backend

Mở `src/services/api.ts` và sửa dòng:

```ts
// Điện thoại thật — cùng WiFi với máy tính
export const API_BASE_URL = 'http://<IP_MÁY_TÍNH>:8000/api'

// Android Emulator
export const API_BASE_URL = 'http://10.0.2.2:8000/api'
```

Tìm IP máy tính:
```bash
# Windows
ipconfig
# Tìm dòng "IPv4 Address" trong mục WiFi adapter
```

---

## Chạy ứng dụng

### Bước 1 — Khởi động backend

```bash
cd ../backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

> `--host 0.0.0.0` bắt buộc để điện thoại kết nối được.

### Bước 2 — Mở firewall (Windows)

```powershell
# Chạy PowerShell với quyền Admin
netsh advfirewall firewall add rule name="FastAPI 8000" dir=in action=allow protocol=TCP localport=8000
```

### Bước 3 — Khởi động Expo

```bash
cd mobile
npx expo start
```

### Bước 4 — Kết nối Expo Go

1. Cài **Expo Go** (SDK 54) trên điện thoại (Android / iOS)
2. Điện thoại và máy tính **phải cùng mạng WiFi**
3. Quét QR code hiển thị trong terminal

---

## Tech Stack

| Thư viện | Phiên bản | Mục đích |
|----------|-----------|----------|
| Expo | ~54.0.0 | Build tool & runtime |
| React Native | 0.81.5 | UI framework |
| React | 19.1.0 | Core |
| React Navigation | 7.x | Stack + Bottom Tab navigation |
| react-native-reanimated | ~4.1.1 | Animation |
| react-native-worklets | ^0.8.1 | Worklets runtime (dep của reanimated v4) |
| Zustand | ^4.5.0 | State management |
| AsyncStorage | ^2.1.0 | Lưu trữ auth token & lịch sử |
| Axios | ^1.7.0 | HTTP client |
| react-native-markdown-display | ^7.0.2 | Render câu trả lời Markdown từ AI |

---

## Lỗi thường gặp

| Lỗi | Nguyên nhân | Cách sửa |
|-----|-------------|----------|
| `Network request failed` | Sai IP hoặc backend chưa chạy | Kiểm tra IP trong `api.ts`, đảm bảo backend bind `0.0.0.0` |
| `Port 8081 in use` | Port bị chiếm | Nhấn **Y** để dùng port khác |
| QR không scan được | Khác mạng WiFi | Dùng `npx expo start --tunnel` |
| `Cannot find module` | Chưa cài package | Chạy `npm install` |
| `SDK mismatch` | Expo Go không đúng version | Cài Expo Go SDK 54 từ App Store / Play Store |
| TS errors trong IDE | tsconfig chưa đúng | `Ctrl+Shift+P` → Restart TS Server |
