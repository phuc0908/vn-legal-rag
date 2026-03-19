import React, { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import Header from '../components/Header'
import Footer from '../components/Footer'
import { getLawStats } from '../services/api'
import '../styles/HomePage.css'

const LAW_CATEGORIES = [
  { icon: '⚖️', label: 'Bộ luật Hình sự', query: 'bộ luật hình sự', color: '#e74c3c' },
  { icon: '📜', label: 'Bộ luật Dân sự', query: 'bộ luật dân sự', color: '#2980b9' },
  { icon: '👷', label: 'Luật Lao động', query: 'bộ luật lao động', color: '#27ae60' },
  { icon: '🏢', label: 'Luật Doanh nghiệp', query: 'luật doanh nghiệp', color: '#8e44ad' },
  { icon: '🏠', label: 'Luật Đất đai', query: 'luật đất đai', color: '#d35400' },
  { icon: '💍', label: 'Hôn nhân & Gia đình', query: 'luật hôn nhân gia đình', color: '#c0392b' },
  { icon: '🚗', label: 'Luật Giao thông', query: 'luật giao thông đường bộ', color: '#16a085' },
  { icon: '🏛️', label: 'Luật Hành chính', query: 'luật hành chính', color: '#2c3e50' },
]

const COMMON_QUESTIONS = [
  'Tội trộm cắp bị phạt bao nhiêu năm?',
  'Quy định về hợp đồng lao động',
  'Thủ tục đăng ký kết hôn',
  'Mức phạt vi phạm giao thông',
  'Quyền và nghĩa vụ của người thuê nhà',
  'Điều kiện thành lập công ty',
]

export default function HomePage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [lawStats, setLawStats] = useState(null)
  const navigate = useNavigate()

  useEffect(() => {
    getLawStats().then(setLawStats).catch(() => {})
  }, [])

  const handleSearch = (e) => {
    e.preventDefault()
    const q = searchQuery.trim()
    if (q) {
      navigate(`/tim-kiem?q=${encodeURIComponent(q)}`)
    }
  }

  const handleQuickSearch = (query) => {
    navigate(`/tim-kiem?q=${encodeURIComponent(query)}`)
  }

  return (
    <div className="home-page">
      <Header />

      {/* Hero Section */}
      <section className="hero">
        <div className="hero-inner">
          <div className="hero-badge">🇻🇳 Hệ thống pháp luật Việt Nam</div>
          <h1 className="hero-title">
            Tra cứu pháp luật<br />
            <span className="hero-accent">nhanh chóng & chính xác</span>
          </h1>
          <p className="hero-subtitle">
            Tìm kiếm thông tin pháp luật, điều luật, quy định từ hàng nghìn văn bản pháp lý Việt Nam.
            Được hỗ trợ bởi công nghệ AI tiên tiến.
          </p>

          <form className="hero-search" onSubmit={handleSearch}>
            <div className="search-input-wrap">
              <span className="search-icon">🔍</span>
              <input
                type="text"
                placeholder="Nhập điều luật, nội dung pháp lý cần tìm..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                autoFocus
              />
              <button type="submit" disabled={!searchQuery.trim()}>
                Tìm kiếm
              </button>
            </div>
          </form>

          <div className="hero-quick">
            <span className="quick-label">Tìm nhanh:</span>
            {COMMON_QUESTIONS.slice(0, 4).map((q) => (
              <button key={q} className="quick-tag" onClick={() => handleQuickSearch(q)}>
                {q}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* Stats */}
      <section className="stats-bar">
        <div className="stats-inner">
          <div className="stat-item">
            <strong>{lawStats ? lawStats.chude : '...'}</strong>
            <span>Chủ đề pháp luật</span>
          </div>
          <div className="stat-divider" />
          <div className="stat-item">
            <strong>{lawStats ? lawStats.demuc : '...'}</strong>
            <span>Đề mục</span>
          </div>
          <div className="stat-divider" />
          <div className="stat-item">
            <strong>{lawStats ? lawStats.dieu.toLocaleString() : '...'}</strong>
            <span>Điều luật</span>
          </div>
          <div className="stat-divider" />
          <div className="stat-item">
            <strong>24/7</strong>
            <span>Tra cứu miễn phí</span>
          </div>
        </div>
      </section>

      {/* Categories */}
      <section className="categories-section">
        <div className="section-inner">
          <h2 className="section-title">Lĩnh vực pháp luật</h2>
          <p className="section-sub">Chọn lĩnh vực để tra cứu các văn bản liên quan</p>
          <div className="categories-grid">
            {LAW_CATEGORIES.map((cat) => (
              <button
                key={cat.label}
                className="category-card"
                onClick={() => handleQuickSearch(cat.query)}
              >
                <span className="cat-icon" style={{ background: cat.color + '18', color: cat.color }}>
                  {cat.icon}
                </span>
                <span className="cat-label">{cat.label}</span>
                <span className="cat-arrow">→</span>
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* Pháp điển Section */}
      <section className="phapdien-section">
        <div className="section-inner">
          <div className="phapdien-card">
            <div className="phapdien-left">
              <div className="phapdien-badge">Mới</div>
              <h2>Hệ thống Pháp điển</h2>
              <p>
                Tra cứu toàn bộ văn bản pháp luật Việt Nam theo cấu trúc phân cấp chính thức:
                Chủ đề → Đề mục → Chương → Điều. Dữ liệu trực tiếp từ hệ thống pháp điển quốc gia.
              </p>
              <div className="phapdien-stats">
                {lawStats && (
                  <>
                    <span><strong>{lawStats.chude}</strong> Chủ đề</span>
                    <span><strong>{lawStats.demuc}</strong> Đề mục</span>
                    <span><strong>{lawStats.chuong}</strong> Chương</span>
                    <span><strong>{lawStats.dieu.toLocaleString()}</strong> Điều</span>
                  </>
                )}
              </div>
              <Link to="/phap-dien" className="phapdien-btn">
                Duyệt Pháp điển →
              </Link>
            </div>
            <div className="phapdien-right">
              <div className="phapdien-tree">
                <div className="ptree-item ptree-l1">📂 Chủ đề</div>
                <div className="ptree-item ptree-l2">📋 Đề mục</div>
                <div className="ptree-item ptree-l3">📑 Chương</div>
                <div className="ptree-item ptree-l4">📄 Điều luật</div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="features-section">
        <div className="section-inner">
          <h2 className="section-title">Tính năng nổi bật</h2>
          <div className="features-grid">
            <div className="feature-card">
              <div className="feature-icon">🔍</div>
              <h3>Tra cứu thông minh</h3>
              <p>Tìm kiếm toàn văn, hiểu ngôn ngữ tự nhiên. Nhập câu hỏi thông thường, hệ thống tự động tìm điều luật phù hợp.</p>
              <button className="feature-btn" onClick={() => navigate('/tim-kiem')}>
                Tra cứu ngay
              </button>
            </div>

            <div className="feature-card featured">
              <div className="feature-badge">Nổi bật</div>
              <div className="feature-icon">🤖</div>
              <h3>Tư vấn AI</h3>
              <p>Đặt câu hỏi bằng tiếng Việt và nhận giải thích chi tiết từ AI. Có trích dẫn nguồn điều luật cụ thể.</p>
              <button className="feature-btn primary" onClick={() => navigate('/tu-van')}>
                Tư vấn ngay
              </button>
            </div>

            <div className="feature-card">
              <div className="feature-icon">📚</div>
              <h3>Dữ liệu đầy đủ</h3>
              <p>Tổng hợp từ các văn bản pháp luật chính thức của Việt Nam, bao gồm các bộ luật, luật và nghị định.</p>
              <button className="feature-btn" onClick={() => navigate('/tim-kiem')}>
                Xem văn bản
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Common Questions */}
      <section className="questions-section">
        <div className="section-inner">
          <h2 className="section-title">Câu hỏi thường gặp</h2>
          <p className="section-sub">Nhấn để tra cứu ngay</p>
          <div className="questions-grid">
            {COMMON_QUESTIONS.map((q) => (
              <button key={q} className="question-card" onClick={() => handleQuickSearch(q)}>
                <span className="q-icon">❓</span>
                <span>{q}</span>
                <span className="q-arrow">→</span>
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Banner */}
      <section className="cta-section">
        <div className="cta-inner">
          <h2>Cần tư vấn pháp lý ngay?</h2>
          <p>Trợ lý AI của chúng tôi sẵn sàng giải đáp mọi thắc mắc pháp lý của bạn 24/7</p>
          <Link to="/tu-van" className="cta-btn">
            Bắt đầu tư vấn miễn phí →
          </Link>
        </div>
      </section>

      <Footer />
    </div>
  )
}
