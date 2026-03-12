import React, { useState } from 'react'
import { sendMessage } from '../services/api'
import '../styles/InputArea.css'

export default function InputArea({ conversation, onAddMessage }) {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSend = async () => {
    if (!input.trim() || !conversation) return

    // Add user message
    const userMessage = {
      role: 'user',
      content: input
    }
    onAddMessage(conversation.id, userMessage)

    setInput('')
    setLoading(true)

    try {
      const response = await sendMessage(input)
      const assistantMessage = {
        role: 'assistant',
        content: response.answer,
        sources: response.sources
      }
      onAddMessage(conversation.id, assistantMessage)
    } catch (error) {
      console.error('Error sending message:', error)
      const errorMessage = {
        role: 'assistant',
        content: 'Xin lỗi, có lỗi xảy ra. Vui lòng thử lại.'
      }
      onAddMessage(conversation.id, errorMessage)
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="input-area">
      <div className="input-container">
        <textarea
          className="input-field"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Hỏi về luật pháp Việt Nam..."
          disabled={loading}
        />
        <button
          className="send-btn"
          onClick={handleSend}
          disabled={loading || !input.trim()}
        >
          {loading ? '⏳' : '➤'}
        </button>
      </div>
    </div>
  )
}
