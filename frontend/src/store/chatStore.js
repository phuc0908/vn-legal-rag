import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useChatStore = create(
  persist(
    (set, get) => ({
      conversations: [],
      currentConversationId: null,

      createConversation: () => {
        const newConv = {
          id: Date.now(),
          title: 'Cuộc trò chuyện mới',
          messages: [],
          createdAt: new Date().toISOString(),
        }
        set((state) => ({
          conversations: [newConv, ...state.conversations],
          currentConversationId: newConv.id,
        }))
        return newConv
      },

      deleteConversation: (id) =>
        set((state) => {
          const filtered = state.conversations.filter((c) => c.id !== id)
          return {
            conversations: filtered,
            currentConversationId:
              state.currentConversationId === id
                ? (filtered[0]?.id ?? null)
                : state.currentConversationId,
          }
        }),

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
    }),
    { name: 'vn-legal-chat-history' }
  )
)
