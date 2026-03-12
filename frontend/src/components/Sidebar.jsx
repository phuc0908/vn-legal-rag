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
      <div className="sidebar-header">
        <button className="new-chat-btn" onClick={onNewChat}>
          + New Chat
        </button>
      </div>
      <div className="conversations-list">
        {conversations.map((conv) => (
          <div
            key={conv.id}
            className={`conversation-item ${
              currentConversation?.id === conv.id ? 'active' : ''
            }`}
            onClick={() => onSelectChat(conv.id)}
          >
            <span className="conv-title">
              {conv.title.length > 20
                ? conv.title.substring(0, 20) + '...'
                : conv.title}
            </span>
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
