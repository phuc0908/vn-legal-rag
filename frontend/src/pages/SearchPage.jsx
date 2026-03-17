import React, { useState, useEffect, useRef } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import Header from '../components/Header'
import Footer from '../components/Footer'
import { sendMessage } from '../services/api'
import '../styles/SearchPage.css'

export default function SearchPage() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const initialQuery = searchParams.get('q') || ''

  const [inputValue, setInputValue] = useState(initialQuery)
  const [query, setQuery] = useState(initialQuery)
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const abortRef = useRef(null)

  useEffect(() => {
    const q = searchParams.get('q') || ''
    setInputValue(q)
    setQuery(q)
  }, [searchParams])

  useEffect(() => {
    if (!query.trim()) {
      setResult(null)
      return
    }
    fetchResult(query)
  }, [query])

  const fetchResult = async (q) => {
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const data = await sendMessage(q)
      setResult(data)
    } catch (err) {
      setError('Không thể kết nối đến máy chủ. Vui lòng thử lại.')
    } finally {
      setLoading(false)
    }
  }

  const handleSearch = (e) => {
    e.preventDefault()
    const q = inputValue.trim()
    if (!q) return
    navigate(`/tim-kiem?q=${encodeURIComponent(q)}`)
  }

  const handleAskAI = () => {
    navigate(`/tu-van?q=${encodeURIComponent(query)}`)
  }

  return (
    <div className="search-page">
      <Header />

      <div className="search-page-body">
        {/* Search Bar */}
        <div className="search-top-bar">
          <div className="search-top-inner">
            <form className="search-form" onSubmit={handleSearch}>
              <div className="search-wrap">
                <span className="s-icon">🔍</span>
                <input
                  type="text"
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  placeholder="Nhập nội dung pháp lý cần tra cứu..."
                  autoFocus
                />
                <button type="submit" disabled={!inputValue.trim()}>
                  Tìm
                </button>
              </div>
            </form>
          </div>
        </div>

        <div className="search-content">
          <div className="search-main">
            {/* Empty state */}
            {!query && !loading && (
              <div className="empty-state">
                <div className="empty-icon">⚖️</div>
                <h3>Tra cứu văn bản pháp luật</h3>
                <p>Nhập từ khóa, câu hỏi hoặc tên điều luật vào ô tìm kiếm phía trên để bắt đầu.</p>
              </div>
            )}

            {/* Loading */}
            {loading && (
              <div className="result-loading">
                <div className="loading-spinner" />
                <p>Đang tìm kiếm trong cơ sở dữ liệu pháp luật...</p>
              </div>
            )}

            {/* Error */}
            {error && !loading && (
              <div className="result-error">
                <span>⚠️</span>
                <p>{error}</p>
                <button onClick={() => fetchResult(query)}>Thử lại</button>
              </div>
            )}

            {/* Result */}
            {result && !loading && (
              <div className="result-wrap">
                <div className="result-header">
                  <h2>Kết quả tra cứu</h2>
                  <span className="result-query">"{query}"</span>
                  {result.processing_time && (
                    <span className="result-meta">
                      {(result.processing_time * 1000).toFixed(0)}ms · {result.model_used || 'AI'}
                    </span>
                  )}
                </div>

                <div className="result-answer-card">
                  <div className="answer-label">
                    <span>⚖️</span> Thông tin pháp lý
                  </div>
                  <div className="answer-body">
                    <ReactMarkdown>{result.answer}</ReactMarkdown>
                  </div>

                  {result.sources && result.sources.length > 0 && (
                    <div className="answer-sources">
                      <h4>Nguồn văn bản tham khảo</h4>
                      <div className="sources-list">
                        {result.sources.map((src, idx) => (
                          <div key={idx} className="source-item">
                            <span className="source-num">{idx + 1}</span>
                            <div className="source-info">
                              <span className="source-title">{src.title || src.source || `Văn bản ${idx + 1}`}</span>
                              {src.score !== undefined && (
                                <span className="source-score">
                                  Độ liên quan: {Math.round(src.score * 100)}%
                                </span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                <div className="result-actions">
                  <button className="action-btn primary" onClick={handleAskAI}>
                    🤖 Hỏi thêm với AI
                  </button>
                  <button className="action-btn" onClick={() => fetchResult(query)}>
                    🔄 Tìm lại
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Sidebar suggestions */}
          <aside className="search-sidebar">
            <div className="sidebar-box">
              <h4>Tìm kiếm liên quan</h4>
              {[
                'Tội trộm cắp tài sản',
                'Hợp đồng lao động',
                'Quyền sử dụng đất',
                'Ly hôn và tài sản',
                'Thành lập doanh nghiệp',
                'Vi phạm giao thông',
              ].map((s) => (
                <button
                  key={s}
                  className="sidebar-link"
                  onClick={() => navigate(`/tim-kiem?q=${encodeURIComponent(s)}`)}
                >
                  🔎 {s}
                </button>
              ))}
            </div>

            <div className="sidebar-box ai-box">
              <div className="ai-box-icon">🤖</div>
              <h4>Cần giải thích chi tiết?</h4>
              <p>Trợ lý AI có thể phân tích và giải thích điều luật theo ngôn ngữ dễ hiểu</p>
              <button
                className="action-btn primary full-width"
                onClick={() => navigate('/tu-van')}
              >
                Tư vấn AI ngay
              </button>
            </div>
          </aside>
        </div>
      </div>

      <Footer />
    </div>
  )
}
