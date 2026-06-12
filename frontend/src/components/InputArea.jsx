import { useState, useEffect } from 'react'
import { getChude, getMyQuota } from '../services/api'
import { useChatStore } from '../store/chatStore'
import { useAuthStore } from '../store/authStore'
import '../styles/InputArea.css'

const MODULES = [
  { id: null,        label: 'Toàn bộ',              icon: '⚖️' },
  { id: 'hon_nhan',  label: 'Hôn nhân & Gia đình',  icon: '👨‍👩‍👧' },
]

export default function InputArea({ conversation, initialQuery = '' }) {
  const [input, setInput] = useState(initialQuery)
  const [chudeList, setChudeList] = useState([])
  const [selectedChudeId, setSelectedChudeId] = useState('')
  const [selectedChudeTen, setSelectedChudeTen] = useState('')
  const [activeModule, setActiveModule] = useState(null)
  const [quota, setQuota] = useState(null)
  const sendQuery = useChatStore((s) => s.sendQuery)
  const pending = useChatStore((s) => s.pending)
  const { user } = useAuthStore()

  // Đang chờ/stream câu trả lời cho ĐÚNG hội thoại hiện tại
  const loading = conversation ? Boolean(pending[conversation.id]) : false

  useEffect(() => {
    getChude()
      .then(data => setChudeList(data))
      .catch(() => {})
  }, [])

  useEffect(() => {
    if (!user?.is_admin) {
      getMyQuota()
        .then(q => setQuota(q))
        .catch(() => {})
    }
  }, [user])

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
    if (moduleId !== null) {
      setSelectedChudeId('')
      setSelectedChudeTen('')
    }
  }

  const activeModuleDef = MODULES.find(m => m.id === activeModule)

  const isQuotaExceeded = quota && !quota.is_admin && quota.limit !== null && quota.remaining === 0

  const handleSend = async () => {
    if (!input.trim() || !conversation || isQuotaExceeded || loading) return

    const trimmed = input.trim()
    const conversationId = conversation.id
    setInput('')

    // Dự đoán quota giảm 1 ngay (sẽ được đồng bộ lại theo kết quả thực tế)
    if (quota && !quota.is_admin && quota.limit !== null) {
      setQuota(q => ({ ...q, used: q.used + 1, remaining: Math.max(0, q.remaining - 1) }))
    }

    // Giao việc gửi/stream cho store — chạy độc lập với component,
    // nên người dùng vẫn có thể đổi hội thoại hoặc chuyển trang.
    const result = await sendQuery({
      conversationId,
      query: trimmed,
      chuDeId: activeModule ? null : (selectedChudeId || null),
      module: activeModule || null,
    })

    if (result?.usage) {
      setQuota(q => q ? { ...q, used: result.usage.used, remaining: result.usage.remaining } : q)
    } else if (result?.status === 429 && result.detail?.limit) {
      setQuota(q => q ? { ...q, remaining: 0, used: result.detail.used ?? q.used } : q)
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const placeholder = isQuotaExceeded
    ? `Bạn đã dùng hết ${quota.limit} câu hỏi hôm nay`
    : activeModule
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
              disabled={loading || isQuotaExceeded}
              title={m.label}
            >
              <span className="module-pill-icon">{m.icon}</span>
              <span className="module-pill-label">{m.label}</span>
            </button>
          ))}
        </div>

        {/* Quota badge */}
        {quota && !quota.is_admin && quota.limit !== null && (
          <div className={`quota-badge${isQuotaExceeded ? ' quota-badge--exceeded' : ''}`}>
            {isQuotaExceeded
              ? `Hết lượt hôm nay (${quota.used}/${quota.limit})`
              : `Còn lại: ${quota.remaining}/${quota.limit} câu`
            }
          </div>
        )}
      </div>

      {/* Chủ đề selector */}
      {activeModule === null && (
        <div className="topic-selector-row">
          <span className="topic-label">Chủ đề:</span>
          <select
            className={`topic-select${selectedChudeId ? ' topic-select--active' : ''}`}
            value={selectedChudeId}
            onChange={handleSelectChude}
            disabled={loading || isQuotaExceeded}
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

      {/* Quota exceeded banner */}
      {isQuotaExceeded && (
        <div className="quota-exceeded-banner">
          Bạn đã đạt giới hạn <strong>{quota.limit} câu hỏi</strong> hôm nay. Vui lòng quay lại vào ngày mai.
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
          disabled={loading || isQuotaExceeded}
        />
        <button
          className="send-btn"
          onClick={handleSend}
          disabled={loading || !input.trim() || isQuotaExceeded}
        >
          {loading ? '⏳' : '➤'}
        </button>
      </div>
    </div>
  )
}
