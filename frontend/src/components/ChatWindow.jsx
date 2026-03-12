import React, { useEffect, useRef } from 'react'
import MessageItem from './MessageItem'
import '../styles/ChatWindow.css'

export default function ChatWindow({ messages }) {
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="chat-window">
      {messages.length === 0 ? (
        <div className="empty-state">
          <h2>Hỏi về Luật Pháp Việt Nam</h2>
          <p>Trợ lý AI sẽ giúp bạn tìm hiểu về các vấn đề pháp lý</p>
        </div>
      ) : (
        <div className="messages">
          {messages.map((msg, index) => (
            <MessageItem key={index} message={msg} />
          ))}
        </div>
      )}
      <div ref={endRef} />
    </div>
  )
}
