import React from 'react'
import ReactMarkdown from 'react-markdown'
import '../styles/MessageItem.css'

export default function MessageItem({ message }) {
  const isUser = message.role === 'user'

  return (
    <div className={`message-item ${isUser ? 'user' : 'assistant'}`}>
      <div className="message-avatar">
        {isUser ? '👤' : '⚖️'}
      </div>
      <div className="message-content">
        {isUser ? (
          <p>{message.content}</p>
        ) : (
          <ReactMarkdown>{message.content}</ReactMarkdown>
        )}
        {message.sources && (
          <div className="message-sources">
            <h4>Nguồn tham khảo:</h4>
            <ul>
              {message.sources.map((source, idx) => (
                <li key={idx}>
                  <a href={source.url} target="_blank" rel="noopener noreferrer">
                    {source.title}
                  </a>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  )
}
