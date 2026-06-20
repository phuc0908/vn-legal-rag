import React, { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Header from '../components/Header'
import Footer from '../components/Footer'
import { getDivorceRoadmap, downloadDivorceTemplate } from '../services/api'
import '../styles/DivorceRoadmapPage.css'

// Nội dung chi tiết của lộ trình được tải từ backend (/roadmap/divorce).
// Người chưa Pro chỉ nhận bản teaser — chi tiết các bước bị khóa không bao giờ
// được gửi xuống trình duyệt nên không thể bị lộ.

export default function DivorceRoadmapPage() {
  const navigate = useNavigate()
  const [steps, setSteps] = useState([])
  const [isPro, setIsPro] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    getDivorceRoadmap()
      .then((data) => {
        setSteps(data.steps || [])
        setIsPro(Boolean(data.is_pro))
      })
      .catch(() => setError('Không tải được lộ trình. Vui lòng thử lại.'))
      .finally(() => setLoading(false))
  }, [])

  // Chatbot mở cho mọi người — chỉ nội dung lộ trình mới giới hạn Pro.
  const handleAsk = (question) => {
    navigate(`/tu-van?q=${encodeURIComponent(question)}&module=hon_nhan`)
  }

  const [downloading, setDownloading] = useState(false)
  const handleDownload = async () => {
    setDownloading(true)
    try {
      const blob = await downloadDivorceTemplate()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'Mau-don-ly-hon.docx'
      document.body.appendChild(a)
      a.click()
      a.remove()
      window.URL.revokeObjectURL(url)
    } catch (e) {
      const status = e.response?.status
      if (status === 404) {
        alert('File mẫu đơn chưa được cập nhật trên hệ thống.')
      } else {
        alert('Không tải được file. Vui lòng thử lại.')
      }
    } finally {
      setDownloading(false)
    }
  }

  return (
    <div className="roadmap-page">
      <Header />
      <div className="roadmap-body">
        <div className="roadmap-hero">
          <span className="roadmap-pro-badge">⭐ Tính năng Pro</span>
          <h1>Lộ trình pháp lý về ly hôn</h1>
          <p>
            Hướng dẫn từng bước thủ tục ly hôn theo pháp luật Việt Nam — từ xác định
            hình thức, chuẩn bị hồ sơ, đến chia tài sản và quyền nuôi con. Mỗi bước
            kèm căn cứ pháp lý và có thể hỏi sâu với trợ lý AI.
          </p>
          <p className="roadmap-disclaimer">
            ⚠️ Nội dung mang tính tham khảo, không thay thế tư vấn của luật sư trong từng vụ việc cụ thể.
          </p>

          {!loading && (
            isPro ? (
              <button
                className="roadmap-download-btn"
                onClick={handleDownload}
                disabled={downloading}
              >
                📥 {downloading ? 'Đang tải...' : 'Tải mẫu đơn ly hôn (.docx)'}
              </button>
            ) : (
              <Link to="/bang-gia" className="roadmap-download-btn roadmap-download-btn--locked">
                🔒 Tải mẫu đơn ly hôn (.docx) — Nâng cấp Pro
              </Link>
            )
          )}
        </div>

        {!loading && !isPro && (
          <div className="roadmap-cta-banner">
            <div className="roadmap-cta-text">
              <strong>Mở khóa toàn bộ lộ trình với gói Pro</strong>
              <span>Xem chi tiết tất cả các bước và căn cứ pháp lý đầy đủ.</span>
            </div>
            <Link to="/bang-gia" className="roadmap-cta-btn">Nâng cấp Pro →</Link>
          </div>
        )}

        {loading && <div className="roadmap-loading">Đang tải lộ trình...</div>}
        {error && <div className="roadmap-error">{error}</div>}

        {!loading && !error && (
          <div className="roadmap-timeline">
            {steps.map((step, index) => {
              const locked = step.locked
              return (
                <div
                  key={index}
                  className={`roadmap-step${locked ? ' roadmap-step--locked' : ''}`}
                >
                  <div className="roadmap-step-marker">
                    <span className="roadmap-step-num">{index + 1}</span>
                  </div>
                  <div className="roadmap-step-card">
                    <div className="roadmap-step-head">
                      <span className="roadmap-step-icon">{step.icon}</span>
                      <h2 className="roadmap-step-title">{step.title}</h2>
                    </div>
                    <p className="roadmap-step-summary">{step.summary}</p>

                    {locked ? (
                      <div className="roadmap-lock-overlay">
                        <span className="roadmap-lock-icon">🔒</span>
                        <span>Nâng cấp gói Pro để xem chi tiết bước này</span>
                        <Link to="/bang-gia" className="roadmap-lock-btn">Mở khóa</Link>
                      </div>
                    ) : (
                      <>
                        <ul className="roadmap-step-points">
                          {(step.points || []).map((p, i) => (
                            <li key={i}>{p}</li>
                          ))}
                        </ul>
                        {step.refs?.length > 0 && (
                          <div className="roadmap-step-refs">
                            <span className="roadmap-refs-label">Căn cứ pháp lý:</span>
                            {step.refs.map((r, i) => (
                              <span key={i} className="roadmap-ref-chip">{r}</span>
                            ))}
                          </div>
                        )}
                        {step.ask && (
                          <button
                            className="roadmap-ask-btn"
                            onClick={() => handleAsk(step.ask)}
                          >
                            💬 Hỏi sâu với trợ lý AI
                          </button>
                        )}
                      </>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}

        {!loading && !isPro && (
          <div className="roadmap-footer-cta">
            <h3>Sẵn sàng đi hết lộ trình?</h3>
            <p>Nâng cấp lên gói Pro để mở khóa toàn bộ hướng dẫn chi tiết và căn cứ pháp lý.</p>
            <Link to="/bang-gia" className="roadmap-cta-btn">Xem các gói cước</Link>
          </div>
        )}
      </div>
      <Footer />
    </div>
  )
}
