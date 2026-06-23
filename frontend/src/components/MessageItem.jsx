import React from 'react'
import ReactMarkdown from 'react-markdown'
import { Link } from 'react-router-dom'
import '../styles/MessageItem.css'

export default function MessageItem({ message }) {
  const isUser = message.role === 'user'
  // Đang chờ token đầu tiên: hiện vòng xoay "đang soạn"
  const isThinking = message.streaming && !message.content

  return (
    <div className={`message-item ${isUser ? 'user' : 'assistant'}`}>
      {!isUser && <div className="message-avatar">⚖️</div>}
      <div className="message-content">
        {isUser ? (
          <p>{message.content}</p>
        ) : isThinking ? (
          <div className="typing-indicator" aria-label="Đang soạn câu trả lời">
            <span></span><span></span><span></span>
          </div>
        ) : (
          <div className={message.streaming ? 'streaming-text' : undefined}>
            <ReactMarkdown>{message.content}</ReactMarkdown>
          </div>
        )}
        {message.sources && message.sources.length > 0 && (
          <div className="message-sources">
            <h4>Nguồn tham khảo:</h4>
            <ul>
              {message.sources.map((source, idx) => (
                <li key={idx}>
                  {source.url?.startsWith('/') ? (
                    <Link to={source.url} target="_blank" rel="noopener noreferrer">
                      {source.title}
                    </Link>
                  ) : source.url ? (
                    <a href={source.url} target="_blank" rel="noopener noreferrer">
                      {source.title}
                    </a>
                  ) : (
                    <span>{source.title}</span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
      {isUser && <div className="message-avatar">👤</div>}
    </div>
  )
}
