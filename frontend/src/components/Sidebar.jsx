import React from 'react'
import '../styles/Sidebar.css'

export default function Sidebar({
  conversations,
  currentConversation,
  onNewChat,
  onSelectChat,
  onDeleteChat,
  isOpen
}) {
  return (
    <div className={`sidebar ${isOpen ? 'open' : 'closed'}`}>
      <div className="sidebar-logo">
        <h2>⚖ Trợ lý Pháp lý</h2>
        <span>Luật Hình sự Việt Nam</span>
      </div>
      <div className="sidebar-header">
        <button className="new-chat-btn" onClick={onNewChat}>
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
    </div>
  )
}
