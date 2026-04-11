import { useState, useEffect } from 'react'
import { sendMessage, getChude } from '../services/api'
import { useChatStore } from '../store/chatStore'
import '../styles/InputArea.css'

const MODULES = [
  { id: null,        label: 'Toàn bộ',              icon: '⚖️' },
  { id: 'hon_nhan',  label: 'Hôn nhân & Gia đình',  icon: '👨‍👩‍👧' },
]

export default function InputArea({ conversation, initialQuery = '' }) {
  const [input, setInput] = useState(initialQuery)
  const [loading, setLoading] = useState(false)
  const [chudeList, setChudeList] = useState([])
  const [selectedChudeId, setSelectedChudeId] = useState('')
  const [selectedChudeTen, setSelectedChudeTen] = useState('')
  const [activeModule, setActiveModule] = useState(null)   // null = full corpus
  const { addMessage, updateTitle } = useChatStore()

  useEffect(() => {
    getChude()
      .then(data => setChudeList(data))
      .catch(() => {})
  }, [])

  const handleSelectChude = (e) => {
    const val = e.target.value
    setSelectedChudeId(val)
    const found = chudeList.find(c => String(c.id) === val)
    setSelectedChudeTen(found?.ten || '')
  }

  const handleClearChude = () => {
    setSelectedChudeId('')
    setSelectedChudeTen('')
  }

  const handleSelectModule = (moduleId) => {
    setActiveModule(moduleId)
    // Khi chọn module chuyên biệt, xóa bộ lọc chủ đề (hai cái loại trừ nhau)
    if (moduleId !== null) {
      setSelectedChudeId('')
      setSelectedChudeTen('')
    }
  }

  const activeModuleDef = MODULES.find(m => m.id === activeModule)

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
      const response = await sendMessage(
        trimmed,
        conversation.id,
        activeModule ? null : (selectedChudeId || null),
        activeModule || null,
      )
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

  const placeholder = activeModule
    ? `Hỏi về "${activeModuleDef?.label}"... (Enter để gửi)`
    : selectedChudeTen
      ? `Hỏi về "${selectedChudeTen}"... (Enter để gửi)`
      : 'Hỏi về luật pháp Việt Nam... (Enter để gửi, Shift+Enter xuống dòng)'

  return (
    <div className="input-area">

      {/* Module selector */}
      <div className="module-selector-row">
        <span className="topic-label">Chế độ:</span>
        <div className="module-pills">
          {MODULES.map(m => (
            <button
              key={String(m.id)}
              className={`module-pill${activeModule === m.id ? ' module-pill--active' : ''}`}
              onClick={() => handleSelectModule(m.id)}
              disabled={loading}
              title={m.label}
            >
              <span className="module-pill-icon">{m.icon}</span>
              <span className="module-pill-label">{m.label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Chủ đề selector — chỉ hiện khi đang ở chế độ Toàn bộ */}
      {activeModule === null && (
        <div className="topic-selector-row">
          <span className="topic-label">Chủ đề:</span>
          <select
            className={`topic-select${selectedChudeId ? ' topic-select--active' : ''}`}
            value={selectedChudeId}
            onChange={handleSelectChude}
            disabled={loading}
          >
            <option value="">Tất cả chủ đề</option>
            {chudeList.map(c => (
              <option key={c.id} value={String(c.id)}>{c.ten}</option>
            ))}
          </select>
          {selectedChudeId && (
            <button
              className="topic-clear-btn"
              onClick={handleClearChude}
              title="Xóa bộ lọc chủ đề"
              disabled={loading}
            >
              ×
            </button>
          )}
        </div>
      )}

      {/* Input */}
      <div className="input-container">
        <textarea
          className="input-field"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
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
