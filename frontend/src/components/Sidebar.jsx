import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import '../styles/Sidebar.css'

export default function Sidebar({
  conversations,
  currentConversation,
  onNewChat,
  onSelectChat,
  onDeleteChat,
  isOpen
}) {
  const [menuOpen, setMenuOpen] = useState(false)
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  // Get initials for avatar
  const getInitials = (name) => {
    if (!name) return 'U'
    return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
  }

  return (
    <div className={`sidebar ${isOpen ? 'open' : 'closed'}`}>
      <div className="sidebar-logo">
        <h2>⚖ Trợ lý Pháp lý</h2>
        <span>Luật Hình sự Việt Nam</span>
      </div>
      <div className="sidebar-header">
        <button className="new-chat-btn" onClick={() => onNewChat()}>
          + Cuộc trò chuyện mới
        </button>
      </div>
      {conversations.length > 0 && (
        <div className="conversations-section-title">Gần đây</div>
      )}
      <div className="conversations-list">
        {conversations.map((conv) => (
          <div
            key={conv.id}
            className={`conversation-item ${
              currentConversation?.id === conv.id ? 'active' : ''
            }`}
            onClick={() => onSelectChat(conv.id)}
          >
            <span className="conv-title">{conv.title}</span>
            <button
              className="delete-btn"
              onClick={(e) => {
                e.stopPropagation()
                onDeleteChat(conv.id)
              }}
            >
              ✕
            </button>
          </div>
        ))}
      </div>

      {/* User Profile Footer */}
      <div className="sidebar-footer">
        {menuOpen && (
          <div className="profile-menu">
            <div className="menu-item" onClick={() => setMenuOpen(false)}>
              <svg className="menu-icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <circle cx="12" cy="12" r="3"></circle>
                <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path>
              </svg>
              Cài đặt
            </div>
            <div className="menu-item" onClick={() => setMenuOpen(false)}>
              <svg className="menu-icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M17 2.1l4 4-4 4"></path>
                <path d="M3 12.2v-2a4 4 0 0 1 4-4h12.8"></path>
                <path d="M7 21.9l-4-4 4-4"></path>
                <path d="M21 11.8v2a4 4 0 0 1-4 4H4.2"></path>
              </svg>
              Đổi tài khoản
            </div>
            <div className="menu-item logout" onClick={handleLogout}>
              <svg className="menu-icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"></path>
                <polyline points="16 17 21 12 16 7"></polyline>
                <line x1="21" y1="12" x2="9" y2="12"></line>
              </svg>
              Đăng xuất
            </div>
          </div>
        )}
        <div className="user-profile" onClick={() => setMenuOpen(!menuOpen)}>
          <div className="avatar">
            {getInitials(user?.full_name || user?.username)}
          </div>
          <div className="user-info">
            <span className="user-name">{user?.full_name || user?.username || 'Người dùng'}</span>
            <span className="user-email">{user?.email || 'Chưa cập nhật email'}</span>
          </div>
          <div className="profile-dots">⋮</div>
        </div>
      </div>
    </div>
  )
}
