import { useState } from 'react'
import { sendMessage } from '../services/api'
import { useChatStore } from '../store/chatStore'
import '../styles/InputArea.css'

export default function InputArea({ conversation, initialQuery = '' }) {
  const [input, setInput] = useState(initialQuery)
  const [loading, setLoading] = useState(false)
  const { addMessage, updateTitle } = useChatStore()

  const handleSend = async () => {
    if (!input.trim() || !conversation) return

    const trimmed = input.trim()

    if (conversation.messages.length === 0) {
      updateTitle(conversation.id, trimmed.substring(0, 45))
    }

    addMessage(conversation.id, { role: 'user', content: trimmed })
    setInput('')
    setLoading(true)

    try {
      const response = await sendMessage(trimmed, conversation.id)
      addMessage(conversation.id, {
        role: 'assistant',
        content: response.answer,
        sources: response.sources,
      })
    } catch (error) {
      addMessage(conversation.id, {
        role: 'assistant',
        content: 'Xin lỗi, có lỗi xảy ra. Vui lòng thử lại.',
      })
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e) => {
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
          onKeyDown={handleKeyDown}
          placeholder="Hỏi về luật pháp Việt Nam... (Enter để gửi, Shift+Enter xuống dòng)"
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
