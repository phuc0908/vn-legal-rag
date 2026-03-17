import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import ChatWindow from '../components/ChatWindow'
import InputArea from '../components/InputArea'
import Sidebar from '../components/Sidebar'
import { useChatStore } from '../store/chatStore'
import '../styles/ChatPage.css'

export default function ChatPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [searchParams] = useSearchParams()
  const { conversations, currentConversationId, createConversation, deleteConversation, selectConversation } =
    useChatStore()

  const currentConversation = conversations.find((c) => c.id === currentConversationId) || null

  useEffect(() => {
    if (conversations.length === 0) {
      createConversation()
    }
  }, [conversations.length])

  // Pre-fill initial query from URL ?q=
  const initialQuery = searchParams.get('q') || ''

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
        <ChatWindow messages={currentConversation?.messages || []} />
        <InputArea conversation={currentConversation} initialQuery={initialQuery} />
      </div>
    </div>
  )
}
