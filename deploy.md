# Deploy Guide

## Kiến trúc

Backend FastAPI phục vụ cả API lẫn frontend đã build — chỉ cần **1 process**.

```
Internet :80/:443
      ↓
   Nginx  (reverse proxy + SSL)
      ↓ :8001
   uvicorn / FastAPI
      ├── /api/*   → RAG pipeline, MySQL, ChromaDB
      └── /*       → React SPA (frontend/dist/)

   MySQL :3306  (cùng server)
   ChromaDB     (thư mục chroma_db/ local)
```

---

## Yêu cầu server

| Thành phần | Tối thiểu |
|---|---|
| OS | Ubuntu 22.04 LTS |
| RAM | **4 GB** (model embedding + reranker ~2–3 GB) |
| CPU | 2 vCPU |
| Disk | 20 GB |
| Port mở | 22 (SSH), 80, 443 |

**Gợi ý nhà cung cấp VPS (giá rẻ):**
- [DigitalOcean](https://digitalocean.com) — $24/tháng (4GB)
- [Vultr](https://vultr.com) — $24/tháng (4GB)  
- [Viettel IDC](https://viettelidc.com.vn), [VNPT Cloud](https://vnptcloud.vn) — tuỳ gói

---

## Bước 1 — Cài đặt server (1 lần)

```bash
# SSH vào server
ssh root@<server-ip>

# Cập nhật hệ thống
apt update && apt upgrade -y

# Cài Python 3.11, pip, git, nginx
apt install -y python3.11 python3.11-venv python3-pip git nginx

# Cài Node.js 20
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

# Cài MySQL
apt install -y mysql-server
mysql_secure_installation  # Đặt mật khẩu root

# Tạo database
mysql -u root -p
# Trong MySQL:
#   CREATE DATABASE law CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
#   CREATE USER 'lawuser'@'localhost' IDENTIFIED BY 'MatKhauManh123!';
#   GRANT ALL ON law.* TO 'lawuser'@'localhost';
#   FLUSH PRIVILEGES; EXIT;
```

---

## Bước 2 — Clone và cấu hình

```bash
cd /srv
git clone https://github.com/phuc0908/vn-legal-rag.git
cd vn-legal-rag

# Cài thư viện backend
cd backend
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Lần đầu sẽ tải model AI từ HuggingFace (~1–2GB, mất vài phút)

# Tạo .env production
cp .env.example .env
nano .env
```

**Nội dung `.env` trên production:**

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here

PORT=8001
DEBUG=False
HOST=0.0.0.0

DB_HOST=localhost
DB_PORT=3306
DB_NAME=law
DB_USER=lawuser
DB_PASSWORD=MatKhauManh123!

# Tạo key: python3 -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=your_random_secret_key_here

# Thay bằng domain thật sau khi có
ALLOWED_ORIGINS=["https://yourdomain.com"]
```

---

## Bước 3 — Build frontend

```bash
cd /srv/vn-legal-rag/frontend
npm install
npm run build
# → frontend/dist/ được tạo, backend sẽ tự serve
```

---

## Bước 4 — Systemd service (tự khởi động lại khi server reboot)

```bash
nano /etc/systemd/system/legal-rag.service
```

```ini
[Unit]
Description=VN Legal RAG API
After=network.target mysql.service

[Service]
User=root
WorkingDirectory=/srv/vn-legal-rag/backend
ExecStart=/srv/vn-legal-rag/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8001 --workers 1
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

```bash
systemctl daemon-reload
systemctl enable legal-rag    # Tự chạy khi reboot
systemctl start legal-rag
systemctl status legal-rag    # Kiểm tra trạng thái
```

---

## Bước 5 — Nginx reverse proxy

```bash
nano /etc/nginx/sites-available/legal-rag
```

```nginx
server {
    listen 80;
    server_name yourdomain.com;   # Hoặc <server-ip> nếu chưa có domain

    client_max_body_size 20M;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 120s;  # RAG pipeline cần thời gian xử lý
    }
}
```

```bash
ln -s /etc/nginx/sites-available/legal-rag /etc/nginx/sites-enabled/
nginx -t                  # Kiểm tra cú pháp
systemctl reload nginx
```

Truy cập thử: `http://<server-ip>`

---

## Bước 6 — SSL miễn phí với Let's Encrypt (cần domain)

```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d yourdomain.com
# Certbot tự sửa file Nginx và cấu hình auto-renew
```

---

## Cập nhật khi có code mới

```bash
cd /srv/vn-legal-rag
git pull origin main

# Nếu có thay đổi frontend
cd frontend && npm run build && cd ..

# Nếu có thay đổi requirements.txt
source backend/venv/bin/activate && pip install -r backend/requirements.txt

# Restart
systemctl restart legal-rag
```

---

## Chạy nhánh thử nghiệm song song trên cùng server

```bash
# Clone nhánh dev vào thư mục riêng
cd /srv
git clone https://github.com/phuc0908/vn-legal-rag.git vn-legal-rag-dev
cd vn-legal-rag-dev
git checkout feat/ten-nhanh

# .env riêng với port khác
cd backend && cp .env.example .env
# Sửa: PORT=8002, DB_NAME=law_dev (tuỳ chọn)

# Build frontend
cd ../frontend && npm install && npm run build

# Systemd service riêng
nano /etc/systemd/system/legal-rag-dev.service
# (giống bước 4 nhưng WorkingDirectory=/srv/vn-legal-rag-dev/backend, port 8002)
systemctl start legal-rag-dev
```

Truy cập nhánh dev: `http://<server-ip>:8002` (hoặc thêm subdomain `dev.yourdomain.com` vào Nginx)

---

## Tóm tắt port

| Service | Port | Mô tả |
|---|---|---|
| Production (`main`) | 8001 | Nginx proxy → internet |
| Dev branch | 8002 | Trực tiếp (nội bộ) |
| Test branch | 8003 | Trực tiếp (nội bộ) |
| MySQL | 3306 | Chỉ localhost |

---

## Xử lý sự cố

```bash
# Xem log realtime
journalctl -u legal-rag -f

# Kiểm tra port đang dùng
ss -tlnp | grep 8001

# Xem log Nginx
tail -f /var/log/nginx/error.log
```
