import React, { useState, useEffect } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import Header from '../components/Header'
import Footer from '../components/Footer'
import { getDieuDetail } from '../services/api'
import '../styles/DieuDetailPage.css'

export default function DieuDetailPage() {
  const { mapc } = useParams()
  const navigate = useNavigate()
  const [dieu, setDieu] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!mapc) return
    setLoading(true)
    setError(null)
    getDieuDetail(decodeURIComponent(mapc))
      .then(setDieu)
      .catch(() => setError('Không tìm thấy điều luật'))
      .finally(() => setLoading(false))
  }, [mapc])

  const handleAskAI = () => {
    if (!dieu) return
    const q = `Giải thích điều ${dieu.chimuc}: ${dieu.ten}`
    navigate(`/tu-van?q=${encodeURIComponent(q)}`)
  }

  return (
    <div className="dieu-detail-page">
      <Header />

      {loading && (
        <div className="dieu-loading">
          <div className="spinner" />
          <p>Đang tải nội dung điều luật...</p>
        </div>
      )}

      {error && (
        <div className="dieu-error">
          <p>{error}</p>
          <Link to="/phap-dien" className="back-btn">← Quay lại Pháp điển</Link>
        </div>
      )}

      {!loading && dieu && (
        <div className="dieu-content-wrap">
          {/* Breadcrumb */}
          <div className="dieu-breadcrumb">
            <Link to="/">Trang chủ</Link>
            <span>›</span>
            <Link to="/phap-dien">Pháp điển</Link>
            {dieu.chude_ten && <><span>›</span><span>{dieu.chude_ten}</span></>}
            {dieu.demuc_ten && <><span>›</span><span>{dieu.demuc_ten}</span></>}
            {dieu.chuong_ten && <><span>›</span><span>Chương {dieu.chuong_chimuc}: {dieu.chuong_ten}</span></>}
            <span>›</span>
            <span className="bc-current">Điều {dieu.chimuc}</span>
          </div>

          <div className="dieu-main">
            {/* Article Content */}
            <article className="dieu-article">
              <div className="article-header">
                <div className="article-num">Điều {dieu.chimuc}</div>
                <h1 className="article-title">{dieu.ten}</h1>
                {dieu.vbqppl && (
                  <div className="article-source">
                    <span className="source-label">Nguồn:</span>
                    {dieu.vbqppl_link ? (
                      <a href={dieu.vbqppl_link} target="_blank" rel="noreferrer" className="source-link">
                        {dieu.vbqppl} ↗
                      </a>
                    ) : (
                      <span>{dieu.vbqppl}</span>
                    )}
                  </div>
                )}
              </div>

              <div className="article-body">
                {dieu.noidung ? (
                  <div
                    className="article-noidung"
                    dangerouslySetInnerHTML={{ __html: dieu.noidung }}
                  />
                ) : (
                  <p className="no-content">Chưa có nội dung</p>
                )}

                {/* HTML Tables embedded in article */}
                {dieu.tables && dieu.tables.length > 0 && (
                  <div className="article-tables">
                    {dieu.tables.map((t) => (
                      <div
                        key={t.id}
                        className="embedded-table"
                        dangerouslySetInnerHTML={{ __html: t.html }}
                      />
                    ))}
                  </div>
                )}
              </div>

              {/* Attached Files */}
              {dieu.files && dieu.files.length > 0 && (
                <div className="article-files">
                  <h3>📎 File đính kèm</h3>
                  <ul>
                    {dieu.files.map((f) => (
                      <li key={f.id}>
                        <a href={f.link} target="_blank" rel="noreferrer">
                          {f.link}
                        </a>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Actions */}
              <div className="article-actions">
                <button className="action-btn primary" onClick={handleAskAI}>
                  🤖 Hỏi AI về điều này
                </button>
                <Link to="/phap-dien" className="action-btn secondary">
                  ← Quay lại Pháp điển
                </Link>
              </div>
            </article>

            {/* Sidebar: Related Articles */}
            {dieu.related && dieu.related.length > 0 && (
              <aside className="dieu-sidebar">
                <div className="sidebar-card">
                  <h3>🔗 Điều liên quan</h3>
                  <ul className="related-list">
                    {dieu.related.map((r) => (
                      <li key={r.mapc}>
                        <Link to={`/phap-dien/dieu/${encodeURIComponent(r.mapc)}`} className="related-link">
                          <span className="related-text">{r.ten}</span>
                          {r.vbqppl && <span className="related-vb">{r.vbqppl}</span>}
                        </Link>
                      </li>
                    ))}
                  </ul>
                </div>
              </aside>
            )}
          </div>
        </div>
      )}

      <Footer />
    </div>
  )
}
