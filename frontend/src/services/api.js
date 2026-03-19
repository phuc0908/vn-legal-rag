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

// ── Law Database API ───────────────────────────────────────────────────────────

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
