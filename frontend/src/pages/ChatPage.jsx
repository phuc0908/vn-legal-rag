import React, { useState, useRef, useEffect } from 'react'
import ChatWindow from '../components/ChatWindow'
import InputArea from '../components/InputArea'
import Sidebar from '../components/Sidebar'
import { useChatStore } from '../store/chatStore'
import '../styles/ChatPage.css'

export default function ChatPage() {
  const [conversations, setConversations] = useState([])
  const [currentConversation, setCurrentConversation] = useState(null)
  const [sidebarOpen, setSidebarOpen] = useState(true)

  const createNewConversation = () => {
    const newConversation = {
      id: Date.now(),
      title: 'New Conversation',
      messages: [],
      createdAt: new Date()
    }
    setConversations([newConversation, ...conversations])
    setCurrentConversation(newConversation)
  }

  const deleteConversation = (id) => {
    const filtered = conversations.filter(c => c.id !== id)
    setConversations(filtered)
    if (currentConversation?.id === id) {
      setCurrentConversation(filtered[0] || null)
    }
  }

  const selectConversation = (id) => {
    const selected = conversations.find(c => c.id === id)
    setCurrentConversation(selected)
  }

  const updateConversationMessages = (conversationId, message) => {
    setConversations(prevConversations =>
      prevConversations.map(conv =>
        conv.id === conversationId
          ? { ...conv, messages: [...conv.messages, message] }
          : conv
      )
    )
  }

  useEffect(() => {
    if (conversations.length === 0) {
      createNewConversation()
    }
  }, [conversations.length])

  return (
    <div className="chat-page">
      <Sidebar
        conversations={conversations}
        currentConversation={currentConversation}
        onNewChat={createNewConversation}
        onSelectChat={selectConversation}
        onDeleteChat={deleteConversation}
        isOpen={sidebarOpen}
      />
      <div className="chat-container">
        <div className="chat-header">
          <button 
            className="menu-btn"
            onClick={() => setSidebarOpen(!sidebarOpen)}
          >
            ☰
          </button>
          <h1>Vietnamese Legal RAG</h1>
          <div className="header-spacer"></div>
        </div>
        <ChatWindow messages={currentConversation?.messages || []} />
        <InputArea conversation={currentConversation} onAddMessage={updateConversationMessages} />
      </div>
    </div>
  )
}
