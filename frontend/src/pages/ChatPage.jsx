import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import ChatWindow from '../components/ChatWindow'
import InputArea from '../components/InputArea'
import Sidebar from '../components/Sidebar'
import { useAuthStore } from '../store/authStore'
import { useChatStore } from '../store/chatStore'
import '../styles/ChatPage.css'

export default function ChatPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [searchParams] = useSearchParams()
  const { isAuthenticated } = useAuthStore()
  const { 
    conversations, 
    currentConversationId, 
    fetchConversations,
    createConversation, 
    deleteConversation,
    selectConversation, 
    addMessage,
    updateTitle,
    isLoading: isChatLoading
  } = useChatStore()

  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  // Sync with backend on mount
  useEffect(() => {
    if (isAuthenticated) {
      fetchConversations()
    }
  }, [isAuthenticated, fetchConversations])

  const currentConversation = conversations.find(c => c.id === currentConversationId)
 || null

  useEffect(() => {
    if (conversations.length === 0) {
      createConversation()
    }
  }, [conversations.length])

  // Pre-fill initial query from URL ?q=
  const initialQuery = searchParams.get('q') || ''

  // Render Auth Guard if not logged in
  if (!isAuthenticated) {
    return (
      <div className="chat-page auth-guard-page">
        <div className="auth-guard-container">
          <div className="auth-guard-card">
            <div className="auth-guard-icon">🔒</div>
            <h2>Bạn chưa đăng nhập</h2>
            <p>Để lưu lại lịch sử tư vấn và trải nghiệm đầy đủ các tính năng của Trợ lý AI, vui lòng đăng nhập hoặc đăng ký tài khoản.</p>
            <div className="auth-guard-actions">
              <Link to="/login" className="login-btn">Đăng nhập ngay</Link>
              <Link to="/register" className="register-btn">Đăng ký tài khoản</Link>
            </div>
            <Link to="/" className="back-home-link">← Quay lại trang chủ</Link>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="chat-page">
      <Sidebar
        conversations={conversations}
        currentConversation={currentConversation}
        onNewChat={createConversation}
        onSelectChat={selectConversation}
        onDeleteChat={deleteConversation}
        isOpen={sidebarOpen}
      />
      <div className="chat-container">
        <div className="chat-header">
          <button className="menu-btn" onClick={() => setSidebarOpen(!sidebarOpen)}>
            ☰
          </button>
          <div className="chat-header-center">
            <Link to="/" className="chat-header-logo">⚖️</Link>
            <h1>Tư vấn Pháp lý AI</h1>
          </div>
          <Link to="/" className="chat-home-link">← Trang chủ</Link>
        </div>
        {isChatLoading ? (
          <div className="chat-loading">Đang tải lịch sử trò chuyện...</div>
        ) : (
          <ChatWindow messages={currentConversation?.messages || []} />
        )}
        <InputArea conversation={currentConversation} initialQuery={initialQuery} />
      </div>
    </div>
  )
}
