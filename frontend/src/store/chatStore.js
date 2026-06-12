import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import {
  getUserConversations,
  createConversation as createConvApi,
  deleteConversation as deleteConvApi,
  streamMessage,
} from '../services/api'

// ── Cấu hình tốc độ "gõ chữ" khi stream (điều chỉnh tại đây) ──────────────────
// Tăng CHAR_DELAY_MS để chậm hơn; giảm để nhanh hơn.
// CHARS_PER_TICK = số ký tự hiện mỗi nhịp (nhỏ = mượt & chậm hơn).
const TYPEWRITER = {
  CHAR_DELAY_MS: 28,   // độ trễ giữa các nhịp (ms) — số càng lớn càng chậm
  CHARS_PER_TICK: 2,   // số ký tự tối thiểu hiện mỗi nhịp
  CATCHUP_DIVISOR: 24, // nếu bộ đệm tồn nhiều, hiện nhanh hơn để không trễ quá
}

export const useChatStore = create(
  persist(
    (set, get) => ({
      conversations: [],
      currentConversationId: null,
      isLoading: false,
      // Trạng thái stream theo từng hội thoại: { [conversationId]: 'thinking' | 'streaming' }
      pending: {},
      // Kết quả lần gửi gần nhất (để InputArea đồng bộ quota)
      lastResult: null,

      fetchConversations: async () => {
        set({ isLoading: true })
        try {
          const data = await getUserConversations()
          const { pending, conversations: existing } = get()
          // Transform backend format to frontend format if needed
          const formatted = data.map(c => {
            // Giữ nguyên message local cho hội thoại đang stream (chưa lưu vào DB)
            if (pending[c.id]) {
              const local = existing.find(e => e.id === c.id)
              if (local) return local
            }
            return {
              id: c.id,
              title: c.title || 'Cuộc trò chuyện mới',
              messages: c.messages || [],
              createdAt: c.created_at
            }
          })
          set({ conversations: formatted })
          const currentId = get().currentConversationId
          const isValid = currentId && formatted.find(c => c.id === currentId)
          if (!isValid && formatted.length > 0) {
            set({ currentConversationId: formatted[0].id })
          }
        } catch (error) {
          console.error('Failed to fetch conversations:', error)
        } finally {
          set({ isLoading: false })
        }
      },

      createConversation: async (title = 'Cuộc trò chuyện mới') => {
        // If title is an event object, use default
        const finalTitle = (typeof title === 'string') ? title : 'Cuộc trò chuyện mới'
        try {
          const newConvData = await createConvApi(finalTitle)
          const newConv = {
            id: newConvData.id,
            title: newConvData.title,
            messages: [],
            createdAt: new Date().toISOString(),
          }
          set((state) => ({
            conversations: [newConv, ...state.conversations],
            currentConversationId: newConv.id,
          }))
          return newConv
        } catch (error) {
          console.error('Failed to create conversation:', error)
          // Fallback to local-only if needed, but better to fail if Auth is core
          return null
        }
      },

      deleteConversation: async (id) => {
        try {
          await deleteConvApi(id)
          set((state) => {
            const filtered = state.conversations.filter((c) => c.id !== id)
            return {
              conversations: filtered,
              currentConversationId:
                state.currentConversationId === id
                  ? (filtered[0]?.id ?? null)
                  : state.currentConversationId,
            }
          })
        } catch (error) {
          console.error('Failed to delete conversation:', error)
        }
      },

      selectConversation: (id) => set({ currentConversationId: id }),

      addMessage: (conversationId, message) =>
        set((state) => ({
          conversations: state.conversations.map((c) =>
            c.id === conversationId
              ? { ...c, messages: [...c.messages, message] }
              : c
          ),
        })),

      updateTitle: (conversationId, title) =>
        set((state) => ({
          conversations: state.conversations.map((c) =>
            c.id === conversationId ? { ...c, title } : c
          ),
        })),

      clearPending: (conversationId) =>
        set((state) => {
          const next = { ...state.pending }
          delete next[conversationId]
          return { pending: next }
        }),

      /**
       * Gửi câu hỏi và stream câu trả lời vào hội thoại tương ứng.
       * Chạy độc lập với component: người dùng có thể đổi hội thoại hoặc
       * chuyển trang khác trong khi vẫn nhận được câu trả lời.
       * Trả về { ok, usage, status, detail }.
       */
      sendQuery: async ({ conversationId, query, chuDeId = null, module = null }) => {
        const trimmed = (query || '').trim()
        if (!trimmed || !conversationId) return { ok: false }

        // Đặt tiêu đề từ câu hỏi đầu tiên
        const conv = get().conversations.find(c => c.id === conversationId)
        if (conv && conv.messages.length === 0) {
          get().updateTitle(conversationId, trimmed.substring(0, 45))
        }

        // Thêm message người dùng + placeholder cho trợ lý (đang suy nghĩ)
        set((state) => ({
          pending: { ...state.pending, [conversationId]: 'thinking' },
          conversations: state.conversations.map((c) =>
            c.id === conversationId
              ? {
                  ...c,
                  messages: [
                    ...c.messages,
                    { role: 'user', content: trimmed },
                    { role: 'assistant', content: '', sources: [], streaming: true },
                  ],
                }
              : c
          ),
        }))

        // Cập nhật message trợ lý (luôn là phần tử cuối của hội thoại)
        const updateAssistant = (updater) =>
          set((state) => ({
            conversations: state.conversations.map((c) => {
              if (c.id !== conversationId) return c
              const messages = c.messages.slice()
              const last = messages.length - 1
              if (last >= 0 && messages[last].role === 'assistant') {
                messages[last] = updater(messages[last])
              }
              return { ...c, messages }
            }),
          }))

        // ── Typewriter: token đổ vào bộ đệm, hiện dần cho mượt & chậm hơn ──
        let buffer = ''            // ký tự đang chờ hiện
        let revealed = 0           // tổng ký tự đã hiện (để xử lý lỗi)
        let streamFinished = false // LLM đã gửi xong chưa
        const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

        const drainLoop = async () => {
          while (true) {
            if (buffer.length === 0) {
              if (streamFinished) break
              await sleep(TYPEWRITER.CHAR_DELAY_MS)
              continue
            }
            // Hiện vài ký tự mỗi nhịp; nếu tồn đọng nhiều thì hiện nhanh hơn để bắt kịp
            const step = Math.max(
              TYPEWRITER.CHARS_PER_TICK,
              Math.floor(buffer.length / TYPEWRITER.CATCHUP_DIVISOR)
            )
            const chunk = buffer.slice(0, step)
            buffer = buffer.slice(step)
            revealed += chunk.length
            set((state) =>
              state.pending[conversationId] === 'streaming'
                ? {}
                : { pending: { ...state.pending, [conversationId]: 'streaming' } }
            )
            updateAssistant((m) => ({ ...m, content: m.content + chunk }))
            await sleep(TYPEWRITER.CHAR_DELAY_MS)
          }
        }

        const drainPromise = drainLoop()

        try {
          const done = await streamMessage(trimmed, conversationId, chuDeId, module, {
            onSources: (sources) => updateAssistant((m) => ({ ...m, sources })),
            onToken: (text) => { buffer += text },
            onError: () => {
              if (revealed === 0 && buffer.length === 0) {
                buffer += 'Xin lỗi, có lỗi xảy ra. Vui lòng thử lại.'
              }
            },
          })
          streamFinished = true
          await drainPromise // chờ hiện hết phần còn lại trong bộ đệm
          updateAssistant((m) => ({ ...m, streaming: false }))
          get().clearPending(conversationId)
          const result = { ok: true, usage: done?.usage ?? null }
          set({ lastResult: result })
          return result
        } catch (error) {
          streamFinished = true
          await drainPromise
          const status = error.status
          const detail = error.detail
          const msg =
            status === 429 && detail?.limit
              ? `Bạn đã sử dụng hết ${detail.limit} câu hỏi cho hôm nay. Vui lòng quay lại vào ngày mai.`
              : 'Xin lỗi, có lỗi xảy ra. Vui lòng thử lại.'
          updateAssistant((m) => ({ ...m, streaming: false, content: m.content || msg }))
          get().clearPending(conversationId)
          const result = { ok: false, status, detail }
          set({ lastResult: result })
          return result
        }
      },

      clearHistory: () => set({ conversations: [], currentConversationId: null, pending: {} })
    }),
    {
      name: 'vn-legal-chat-history',
      // Chỉ lưu hội thoại; trạng thái stream/loading không nên được persist
      partialize: (state) => ({
        conversations: state.conversations,
        currentConversationId: state.currentConversationId,
      }),
    }
  )
)
