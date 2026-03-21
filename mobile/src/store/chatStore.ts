import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import AsyncStorage from '@react-native-async-storage/async-storage'
import {
  getUserConversations,
  createConversation as createConvApi,
  deleteConversation as deleteConvApi,
} from '../services/api'
import { ChatState, Conversation, Message } from '../types'

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      conversations: [],
      currentConversationId: null,
      isLoading: false,

      fetchConversations: async () => {
        set({ isLoading: true })
        try {
          const data = await getUserConversations()
          const formatted: Conversation[] = data.map((c: any) => ({
            id: c.id,
            title: c.title || 'Cuộc trò chuyện mới',
            messages: c.messages || [],
            createdAt: c.created_at,
          }))
          set({ conversations: formatted })
          const currentId = get().currentConversationId
          const isValid = currentId && formatted.find((c) => c.id === currentId)
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
        try {
          const data = await createConvApi(title)
          const newConv: Conversation = {
            id: data.id,
            title: data.title,
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
          return null
        }
      },

      deleteConversation: async (id: string) => {
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

      selectConversation: (id: string) => set({ currentConversationId: id }),

      addMessage: (conversationId: string, message: Message) =>
        set((state) => ({
          conversations: state.conversations.map((c) =>
            c.id === conversationId
              ? { ...c, messages: [...c.messages, message] }
              : c
          ),
        })),

      updateTitle: (conversationId: string, title: string) =>
        set((state) => ({
          conversations: state.conversations.map((c) =>
            c.id === conversationId ? { ...c, title } : c
          ),
        })),

      clearHistory: () =>
        set({ conversations: [], currentConversationId: null }),
    }),
    {
      name: 'vn-legal-chat-history',
      storage: createJSONStorage(() => AsyncStorage),
    }
  )
)
