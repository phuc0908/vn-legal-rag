import axios from 'axios'
import { useAuthStore } from '../store/authStore'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add Auth Header Interceptor
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
}, (error) => {
  return Promise.reject(error)
})

// Handle 401 Unauthorized globally
apiClient.interceptors.response.use((response) => response, (error) => {
  if (error.response?.status === 401) {
    useAuthStore.getState().logout()
  }
  return Promise.reject(error)
})

// ── Auth API ───────────────────────────────────────────────────────────────────

export const login = async (username, password) => {
  const formData = new FormData()
  formData.append('username', username)
  formData.append('password', password)
  
  const response = await apiClient.post('/auth/login', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
  return response.data
}

export const register = async (userData) => {
  const response = await apiClient.post('/auth/register', userData)
  return response.data
}

export const getMe = async () => {
  const response = await apiClient.get('/auth/me')
  return response.data
}

// ── Conversation API ──────────────────────────────────────────────────────────

export const getUserConversations = async () => {
  const response = await apiClient.get('/conversations/')
  return response.data
}

export const createConversation = async (title) => {
  const response = await apiClient.post('/conversations/', null, { params: { title } })
  return response.data
}

// ── Chat API ───────────────────────────────────────────────────────────────────

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

// ── Law Database API ───────────────────────────────────────────────────────────
// ... rest of the file

export const getLawStats = async () => {
  const response = await apiClient.get('/law/stats')
  return response.data
}

export const getChude = async () => {
  const response = await apiClient.get('/law/chude')
  return response.data
}

export const getDemuc = async (chudeId) => {
  const response = await apiClient.get('/law/demuc', { params: { chude_id: chudeId } })
  return response.data
}

export const getChuong = async (demucId) => {
  const response = await apiClient.get('/law/chuong', { params: { demuc_id: demucId } })
  return response.data
}

export const getDieuList = async ({ chuongId, demucId }) => {
  const params = {}
  if (chuongId) params.chuong_id = chuongId
  if (demucId) params.demuc_id = demucId
  const response = await apiClient.get('/law/dieu/list', { params })
  return response.data
}

export const getDieuDetail = async (mapc) => {
  const response = await apiClient.get(`/law/dieu/${encodeURIComponent(mapc)}`)
  return response.data
}

export const searchLaw = async (q, page = 1, size = 20) => {
  const response = await apiClient.get('/law/search', { params: { q, page, size } })
  return response.data
}

export default apiClient
