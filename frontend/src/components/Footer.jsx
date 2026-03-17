import React from 'react'
import { Link } from 'react-router-dom'
import '../styles/Footer.css'

export default function Footer() {
  return (
    <footer className="site-footer">
      <div className="footer-inner">
        <div className="footer-brand">
          <Link to="/" className="footer-logo">
            <span>⚖️</span> Pháp Lý Việt Nam
          </Link>
          <p>Hệ thống tra cứu pháp luật và tư vấn pháp lý ứng dụng trí tuệ nhân tạo, giúp người dân dễ dàng tiếp cận thông tin pháp luật.</p>
        </div>

        <div className="footer-col">
          <h4>Tra cứu</h4>
          <Link to="/tim-kiem?q=bộ luật hình sự">Bộ luật Hình sự</Link>
          <Link to="/tim-kiem?q=bộ luật dân sự">Bộ luật Dân sự</Link>
          <Link to="/tim-kiem?q=luật lao động">Luật Lao động</Link>
          <Link to="/tim-kiem?q=luật đất đai">Luật Đất đai</Link>
          <Link to="/tim-kiem?q=luật doanh nghiệp">Luật Doanh nghiệp</Link>
        </div>

        <div className="footer-col">
          <h4>Tiện ích</h4>
          <Link to="/tu-van">Tư vấn AI</Link>
          <Link to="/tim-kiem">Tìm kiếm văn bản</Link>
          <Link to="/">Trang chủ</Link>
        </div>
      </div>

      <div className="footer-bottom">
        <p>© 2025 Pháp Lý Việt Nam · Đồ án tốt nghiệp · Dữ liệu mang tính tham khảo, không thay thế tư vấn pháp lý chuyên nghiệp</p>
      </div>
    </footer>
  )
}
