import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

export const sendMessage = async (message, conversationId) => {
  try {
    const response = await apiClient.post('/query', {
      query: message,
      conversation_id: conversationId ? String(conversationId) : undefined,
    })
    return response.data
  } catch (error) {
    console.error('API Error:', error)
    throw error
  }
}

export const getConversationHistory = async (conversationId) => {
  try {
    const response = await apiClient.get(`/conversation/${conversationId}`)
    return response.data
  } catch (error) {
    console.error('API Error:', error)
    throw error
  }
}

export default apiClient
