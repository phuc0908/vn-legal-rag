import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { getUserConversations, createConversation as createConvApi, deleteConversation as deleteConvApi } from '../services/api'

export const useChatStore = create(
  persist(
    (set, get) => ({
      conversations: [],
      currentConversationId: null,
      isLoading: false,

      fetchConversations: async () => {
        set({ isLoading: true })
        try {
          const data = await getUserConversations()
          // Transform backend format to frontend format if needed
          const formatted = data.map(c => ({
            id: c.id,
            title: c.title || 'Cuộc trò chuyện mới',
            messages: c.messages || [],
            createdAt: c.created_at
          }))
          set({ conversations: formatted })
          if (formatted.length > 0 && !get().currentConversationId) {
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
        
      clearHistory: () => set({ conversations: [], currentConversationId: null })
    }),
    { name: 'vn-legal-chat-history' }
  )
)
