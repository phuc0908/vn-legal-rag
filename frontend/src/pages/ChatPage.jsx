import { useEffect, useState } from 'react'
import ChatWindow from '../components/ChatWindow'
import InputArea from '../components/InputArea'
import Sidebar from '../components/Sidebar'
import { useChatStore } from '../store/chatStore'
import '../styles/ChatPage.css'

export default function ChatPage() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const { conversations, currentConversationId, createConversation, deleteConversation, selectConversation } =
    useChatStore()

  const currentConversation = conversations.find((c) => c.id === currentConversationId) || null

  useEffect(() => {
    if (conversations.length === 0) {
      createConversation()
    }
  }, [conversations.length])

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
          <h1>Trợ Lý Pháp Lý Việt Nam</h1>
          <div className="header-spacer"></div>
        </div>
        <ChatWindow messages={currentConversation?.messages || []} />
        <InputArea conversation={currentConversation} />
      </div>
    </div>
  )
}
