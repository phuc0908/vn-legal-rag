import React, { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Header from '../components/Header'
import Footer from '../components/Footer'
import { getBookmarks, removeBookmark, getHistory, removeHistoryItem, clearHistory } from '../services/api'
import { useAuthStore } from '../store/authStore'
import '../styles/SavedPage.css'

function BreadcrumbBar({ item, type }) {
  const navigate = useNavigate()

  const goToBrowser = (params) => {
    navigate(`/phap-dien?${new URLSearchParams(params).toString()}`)
  }

  return (
    <div className="saved-breadcrumb">
      <button className="bc-btn" onClick={() => navigate('/phap-dien')}>
        Pháp điển
      </button>
      {item.chude_ten && (
        <>
          <span className="bc-sep">›</span>
          <button
            className="bc-btn"
            onClick={() => goToBrowser({ chude_id: item.chude_id })}
            title="Mở trong cây pháp điển"
          >
            {item.chude_ten}
          </button>
        </>
      )}
      {item.demuc_ten && (
        <>
          <span className="bc-sep">›</span>
          <button
            className="bc-btn"
            onClick={() => goToBrowser({ chude_id: item.chude_id, demuc_id: item.demuc_id })}
            title="Mở trong cây pháp điển"
          >
            {item.demuc_ten}
          </button>
        </>
      )}
      {item.chuong_ten && (
        <>
          <span className="bc-sep">›</span>
          <button
            className="bc-btn"
            onClick={() =>
              goToBrowser({
                chude_id: item.chude_id,
                demuc_id: item.demuc_id,
                chuong_id: item.chuong_id,
              })
            }
            title="Mở trong cây pháp điển"
          >
            {item.chuong_chimuc ? `Chương ${item.chuong_chimuc}` : item.chuong_ten}
          </button>
        </>
      )}
    </div>
  )
}

function DieuCard({ item, type, onRemove }) {
  return (
    <div className="saved-card">
      <div className="saved-card-main">
        <BreadcrumbBar item={item} type={type} />
        <Link
          to={`/phap-dien/dieu/${encodeURIComponent(item.mapc)}`}
          className="saved-dieu-title"
        >
          <span className="saved-dieu-num">Điều {item.chimuc}</span>
          <span className="saved-dieu-name">{item.ten}</span>
        </Link>
        {item.vbqppl && <span className="saved-vbqppl">{item.vbqppl}</span>}
      </div>
      <div className="saved-card-meta">
        {type === 'bookmark' && item.created_at && (
          <span className="saved-date">
            Lưu lúc {new Date(item.created_at).toLocaleDateString('vi-VN')}
          </span>
        )}
        {type === 'history' && item.viewedAt && (
          <span className="saved-date">
            Xem lúc {new Date(item.viewedAt).toLocaleString('vi-VN', { dateStyle: 'short', timeStyle: 'short' })}
          </span>
        )}
        <button className="saved-remove-btn" onClick={() => onRemove(item.mapc)}>
          Xóa
        </button>
      </div>
    </div>
  )
}

export default function SavedPage() {
  const { isAuthenticated } = useAuthStore()
  const navigate = useNavigate()
  const [tab, setTab] = useState('bookmarks')

  const [bookmarks, setBookmarks] = useState([])
  const [bookmarkLoading, setBookmarkLoading] = useState(false)
  const [history, setHistory] = useState([])
  const [historyLoading, setHistoryLoading] = useState(false)

  useEffect(() => {
    if (!isAuthenticated) return
    if (tab === 'bookmarks') {
      setBookmarkLoading(true)
      getBookmarks()
        .then(setBookmarks)
        .catch(() => {})
        .finally(() => setBookmarkLoading(false))
    } else {
      setHistoryLoading(true)
      getHistory()
        .then(h => setHistory(h.map(item => ({ ...item, viewedAt: item.viewed_at }))))
        .catch(() => {})
        .finally(() => setHistoryLoading(false))
    }
  }, [tab, isAuthenticated])

  const handleRemoveBookmark = async (mapc) => {
    try {
      await removeBookmark(mapc)
      setBookmarks(prev => prev.filter(b => b.mapc !== mapc))
    } catch {}
  }

  const handleRemoveHistory = async (mapc) => {
    try {
      await removeHistoryItem(mapc)
      setHistory(prev => prev.filter(h => h.mapc !== mapc))
    } catch {}
  }

  const handleClearHistory = async () => {
    try {
      await clearHistory()
      setHistory([])
    } catch {}
  }

  return (
    <div className="saved-page">
      <Header />
      <div className="saved-body">
        <div className="saved-header">
          <h1>Thư viện của tôi</h1>
          <p>Điều luật đã lưu và lịch sử xem gần đây</p>
        </div>

        <div className="saved-tabs">
          <button
            className={`tab-btn ${tab === 'bookmarks' ? 'active' : ''}`}
            onClick={() => setTab('bookmarks')}
          >
            ★ Đã lưu {bookmarks.length > 0 && <span className="tab-count">{bookmarks.length}</span>}
          </button>
          <button
            className={`tab-btn ${tab === 'history' ? 'active' : ''}`}
            onClick={() => setTab('history')}
          >
            🕐 Lịch sử xem {history.length > 0 && <span className="tab-count">{history.length}</span>}
          </button>
        </div>

        {/* Bookmarks tab */}
        {tab === 'bookmarks' && (
          <div className="saved-content">
            {!isAuthenticated ? (
              <div className="saved-empty">
                <div className="empty-icon">🔒</div>
                <h3>Cần đăng nhập</h3>
                <p>Đăng nhập để lưu và xem lại các điều luật quan tâm.</p>
                <button className="cta-btn" onClick={() => navigate('/login')}>
                  Đăng nhập ngay
                </button>
              </div>
            ) : bookmarkLoading ? (
              <div className="saved-loading">Đang tải...</div>
            ) : bookmarks.length === 0 ? (
              <div className="saved-empty">
                <div className="empty-icon">☆</div>
                <h3>Chưa có điều luật nào được lưu</h3>
                <p>Mở bất kỳ điều luật và nhấn "Lưu lại" để thêm vào đây.</p>
                <button className="cta-btn" onClick={() => navigate('/phap-dien')}>
                  Duyệt Pháp điển
                </button>
              </div>
            ) : (
              <div className="saved-list">
                {bookmarks.map(b => (
                  <DieuCard
                    key={b.mapc}
                    item={b}
                    type="bookmark"
                    onRemove={handleRemoveBookmark}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {/* History tab */}
        {tab === 'history' && (
          <div className="saved-content">
            {!isAuthenticated ? (
              <div className="saved-empty">
                <div className="empty-icon">🔒</div>
                <h3>Cần đăng nhập</h3>
                <p>Đăng nhập để lưu lịch sử xem vào tài khoản.</p>
                <button className="cta-btn" onClick={() => navigate('/login')}>
                  Đăng nhập ngay
                </button>
              </div>
            ) : historyLoading ? (
              <div className="saved-loading">Đang tải...</div>
            ) : history.length === 0 ? (
              <div className="saved-empty">
                <div className="empty-icon">🕐</div>
                <h3>Chưa có lịch sử xem</h3>
                <p>Các điều luật bạn đã xem sẽ tự động xuất hiện ở đây.</p>
                <button className="cta-btn" onClick={() => navigate('/phap-dien')}>
                  Duyệt Pháp điển
                </button>
              </div>
            ) : (
              <>
                <div className="saved-toolbar">
                  <span className="toolbar-info">{history.length} điều luật đã xem</span>
                  <button className="clear-btn" onClick={handleClearHistory}>
                    Xóa tất cả
                  </button>
                </div>
                <div className="saved-list">
                  {history.map(h => (
                    <DieuCard
                      key={h.mapc}
                      item={h}
                      type="history"
                      onRemove={handleRemoveHistory}
                    />
                  ))}
                </div>
              </>
            )}
          </div>
        )}
      </div>
      <Footer />
    </div>
  )
}
