import React, { useState, useEffect } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import Header from '../components/Header'
import Footer from '../components/Footer'
import { getDieuDetail, toggleBookmark, getBookmarkStatus, addHistory } from '../services/api'
import { useAuthStore } from '../store/authStore'
import '../styles/DieuDetailPage.css'

function formatCitation(vbqppl, demucTen) {
  if (!vbqppl || !demucTen) return null
  const dieuMatch = vbqppl.match(/Điều\s+(\d+)/)
  const yearMatch = vbqppl.match(/số\s+\d+\/(\d{4})\//)
  if (!dieuMatch || !yearMatch) return null
  return `Điều ${dieuMatch[1]} Luật ${demucTen} ${yearMatch[1]}`
}

function cleanDieuTen(ten) {
  if (!ten) return ''
  return ten.replace(/^Điều\s+[\d.A-Za-z]+\.\s*/, '').trim()
}

export default function DieuDetailPage() {
  const { mapc } = useParams()
  const navigate = useNavigate()
  const { isAuthenticated } = useAuthStore()

  const [dieu, setDieu] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [bookmarked, setBookmarked] = useState(false)
  const [bookmarkLoading, setBookmarkLoading] = useState(false)
  const [bookmarkError, setBookmarkError] = useState(null)

  useEffect(() => {
    if (!mapc) return
    setLoading(true)
    setError(null)
    getDieuDetail(decodeURIComponent(mapc))
      .then((data) => {
        setDieu(data)
        if (isAuthenticated) {
          const entry = {
            mapc: String(data.mapc),
            chimuc: data.chimuc != null ? String(data.chimuc) : null,
            ten: data.ten != null ? String(data.ten) : null,
            vbqppl: data.vbqppl != null ? String(data.vbqppl) : null,
            chude_id: data.chude_id != null ? String(data.chude_id) : null,
            chude_ten: data.chude_ten != null ? String(data.chude_ten) : null,
            demuc_id: data.demuc_id != null ? String(data.demuc_id) : null,
            demuc_ten: data.demuc_ten != null ? String(data.demuc_ten) : null,
            chuong_id: data.chuong_id != null ? String(data.chuong_id) : null,
            chuong_ten: data.chuong_ten != null ? String(data.chuong_ten) : null,
            chuong_chimuc: data.chuong_chimuc != null ? String(data.chuong_chimuc) : null,
          }
          addHistory(entry).catch(() => {})
          getBookmarkStatus(data.mapc).then(r => setBookmarked(r.bookmarked)).catch(() => {})
        }
      })
      .catch(() => setError('Không tìm thấy điều luật'))
      .finally(() => setLoading(false))
  }, [mapc, isAuthenticated])

  const handleAskAI = () => {
    if (!dieu) return
    const q = `Giải thích điều ${dieu.chimuc}: ${dieu.ten}`
    navigate(`/tu-van?q=${encodeURIComponent(q)}`)
  }

  const handleToggleBookmark = async () => {
    if (!isAuthenticated) {
      navigate('/login')
      return
    }
    setBookmarkLoading(true)
    setBookmarkError(null)
    try {
      const payload = {
        mapc: String(dieu.mapc),
        chimuc: dieu.chimuc != null ? String(dieu.chimuc) : null,
        ten: dieu.ten != null ? String(dieu.ten) : null,
        vbqppl: dieu.vbqppl != null ? String(dieu.vbqppl) : null,
        chude_id: dieu.chude_id != null ? String(dieu.chude_id) : null,
        chude_ten: dieu.chude_ten != null ? String(dieu.chude_ten) : null,
        demuc_id: dieu.demuc_id != null ? String(dieu.demuc_id) : null,
        demuc_ten: dieu.demuc_ten != null ? String(dieu.demuc_ten) : null,
        chuong_id: dieu.chuong_id != null ? String(dieu.chuong_id) : null,
        chuong_ten: dieu.chuong_ten != null ? String(dieu.chuong_ten) : null,
        chuong_chimuc: dieu.chuong_chimuc != null ? String(dieu.chuong_chimuc) : null,
      }
      const result = await toggleBookmark(payload)
      setBookmarked(result.bookmarked)
    } catch (err) {
      const detail = err?.response?.data?.detail
      let msg
      if (Array.isArray(detail)) {
        // Pydantic validation errors — lấy field + message
        msg = detail.map(e => `${e.loc?.slice(-1)[0] ?? ''}: ${e.msg}`).join(' | ')
      } else {
        msg = detail || err?.message || 'Lỗi không xác định'
      }
      setBookmarkError(String(msg))
      console.error('Bookmark error:', err?.response?.status, detail)
    } finally {
      setBookmarkLoading(false)
    }
  }

  // Format content to handle lists like 1., 2., a), b)
  const formatLegalContent = (text) => {
    if (!text) return ''
    let processed = text.replace(/\n\s*\n+/g, '\n')
    processed = processed.replace(/(\s|^)(\d+\.)\s/g, '\n$2 ')
    processed = processed.replace(/(\s|^)([a-z]\))\s/g, '\n$2 ')
    const lines = processed.split('\n').map(l => l.trim()).filter(l => l.length > 0)
    let inSubItem = false
    return lines.map(line => {
      if (/^[a-z]\)/i.test(line)) {
        inSubItem = true
        return `<div class="dieu-sub-item">${line}</div>`
      }
      if (/^\d+\./.test(line)) {
        inSubItem = false
        return `<div class="dieu-item">${line}</div>`
      }
      if (inSubItem && (line.toLowerCase().startsWith('ví dụ') || line.toLowerCase().startsWith('ghi chú'))) {
        return `<div class="dieu-sub-item-text">${line}</div>`
      }
      return `<div class="dieu-text-line">${line}</div>`
    }).join('')
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
          {/* Breadcrumb — clickable, tra ngược về cây phân cấp */}
          <div className="dieu-breadcrumb">
            <Link to="/">Trang chủ</Link>
            <span>›</span>
            <Link to="/phap-dien">Pháp điển</Link>
            {dieu.chude_ten && (
              <>
                <span>›</span>
                <Link
                  to={`/phap-dien?chude_id=${dieu.chude_id}`}
                  className="bc-link"
                >
                  {dieu.chude_ten}
                </Link>
              </>
            )}
            {dieu.demuc_ten && (
              <>
                <span>›</span>
                <Link
                  to={`/phap-dien?chude_id=${dieu.chude_id}&demuc_id=${dieu.demuc_id}`}
                  className="bc-link"
                >
                  {dieu.demuc_ten}
                </Link>
              </>
            )}
            {dieu.chuong_ten && (
              <>
                <span>›</span>
                <Link
                  to={`/phap-dien?chude_id=${dieu.chude_id}&demuc_id=${dieu.demuc_id}&chuong_id=${encodeURIComponent(dieu.chuong_id)}`}
                  className="bc-link"
                >
                  Chương {dieu.chuong_chimuc}: {dieu.chuong_ten}
                </Link>
              </>
            )}
            <span>›</span>
            <span className="bc-current">Điều {dieu.chimuc}</span>
          </div>

          <div className="dieu-main">
            {/* Article Content */}
            <article className="dieu-article">
              <div className="article-header">
                <div className="article-header-top">
                  <div className="article-num">
                    {formatCitation(dieu.vbqppl, dieu.demuc_ten) || `Điều ${dieu.chimuc}`}
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
                    <button
                      className={`bookmark-btn ${bookmarked ? 'bookmarked' : ''}`}
                      onClick={handleToggleBookmark}
                      disabled={bookmarkLoading}
                      title={bookmarked ? 'Bỏ lưu' : 'Lưu điều luật này'}
                    >
                      {bookmarkLoading ? '...' : bookmarked ? '★ Đã lưu' : '☆ Lưu lại'}
                    </button>
                    {bookmarkError && (
                      <span style={{ fontSize: 11, color: '#ef4444' }}>{bookmarkError}</span>
                    )}
                  </div>
                </div>
                <h1 className="article-title">{cleanDieuTen(dieu.ten)}</h1>
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
                    dangerouslySetInnerHTML={{ __html: formatLegalContent(dieu.noidung) }}
                  />
                ) : (
                  <p className="no-content">Chưa có nội dung</p>
                )}

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

              {dieu.files && dieu.files.length > 0 && (
                <div className="article-files">
                  <h3>📎 File đính kèm</h3>
                  <ul>
                    {dieu.files.map((f) => (
                      <li key={f.id}>
                        <a href={f.link} target="_blank" rel="noreferrer">{f.link}</a>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="article-actions">
                <button className="action-btn primary" onClick={handleAskAI}>
                  🤖 Hỏi AI về điều này
                </button>
                <Link to="/phap-dien" className="action-btn secondary">
                  ← Quay lại Pháp điển
                </Link>
              </div>
            </article>

            {dieu.related && dieu.related.length > 0 && (
              <aside className="dieu-sidebar">
                <div className="sidebar-card">
                  <h3>🔗 Điều liên quan</h3>
                  <ul className="related-list">
                    {dieu.related.map((r) => (
                      <li key={r.mapc}>
                        <Link to={`/phap-dien/dieu/${encodeURIComponent(r.mapc)}`} className="related-link">
                          <span className="related-vb">
                            {formatCitation(r.vbqppl, r.demuc_ten) || r.ten}
                          </span>
                          <span className="related-text">{cleanDieuTen(r.ten)}</span>
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
