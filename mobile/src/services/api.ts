import axios from 'axios'
import { useAuthStore } from '../store/authStore'


// Máy tính cùng mạng WiFi với điện thoại:
//   - Tìm IP bằng: ipconfig (Windows) hoặc ifconfig (Mac/Linux)
//   - Ví dụ: http://192.168.1.5:8000/api
// Android Emulator: http://10.0.2.2:8000/api
export const API_BASE_URL = 'http://192.168.2.8:8000/api'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
})

// Gắn token vào mỗi request
apiClient.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Tự logout khi nhận 401
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      useAuthStore.getState().logout()
    }
    return Promise.reject(error)
  }
)

// ── Auth ──────────────────────────────────────────────────────────────────────

export const login = async (username: string, password: string) => {
  const params = new URLSearchParams()
  params.append('username', username)
  params.append('password', password)
  const response = await apiClient.post('/auth/login', params.toString(), {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  return response.data as { access_token: string; token_type: string }
}

export const register = async (data: {
  username: string
  password: string
  full_name?: string
  email?: string
}) => {
  const response = await apiClient.post('/auth/register', data)
  return response.data
}

export const getMe = async () => {
  const response = await apiClient.get('/auth/me')
  return response.data
}

// ── Conversations ─────────────────────────────────────────────────────────────

export const getUserConversations = async () => {
  const response = await apiClient.get('/conversations/')
  return response.data
}

export const createConversation = async (title?: string) => {
  const response = await apiClient.post('/conversations/', null, {
    params: { title },
  })
  return response.data
}

export const deleteConversation = async (id: string) => {
  const response = await apiClient.delete(`/conversations/${id}`)
  return response.data
}

// ── Chat / RAG ────────────────────────────────────────────────────────────────

export const sendMessage = async (
  message: string,
  conversationId: string | null,
  chuDeId: string | null = null
) => {
  const body: Record<string, unknown> = {
    query: message,
    conversation_id: conversationId ?? undefined,
  }
  if (chuDeId) body.chu_de_id = chuDeId
  const response = await apiClient.post('/query', body)
  return response.data
}

// ── Law / Pháp điển ───────────────────────────────────────────────────────────

export const getLawStats = async () => {
  const response = await apiClient.get('/law/stats')
  return response.data
}

export const getChude = async () => {
  const response = await apiClient.get('/law/chude')
  return response.data
}

export const getDemuc = async (chudeId: number) => {
  const response = await apiClient.get('/law/demuc', {
    params: { chude_id: chudeId },
  })
  return response.data
}

export const getChuong = async (demucId: number) => {
  const response = await apiClient.get('/law/chuong', {
    params: { demuc_id: demucId },
  })
  return response.data
}

export const getDieuList = async ({
  chuongId,
  demucId,
}: {
  chuongId?: string
  demucId?: number
}) => {
  const params: Record<string, unknown> = {}
  if (chuongId) params.chuong_id = chuongId
  if (demucId) params.demuc_id = demucId
  const response = await apiClient.get('/law/dieu/list', { params })
  return response.data
}

export const getDieuDetail = async (mapc: string) => {
  const response = await apiClient.get(`/law/dieu/${encodeURIComponent(mapc)}`)
  return response.data
}

export const searchLaw = async (q: string, page = 1, size = 20) => {
  const response = await apiClient.get('/law/search', {
    params: { q, page, size },
  })
  return response.data
}

// ── Bookmark API ──────────────────────────────────────────────────────────────

export const getBookmarks = async () => {
  const response = await apiClient.get('/bookmarks/')
  return response.data
}

export const toggleBookmark = async (dieuData: Record<string, unknown>) => {
  const response = await apiClient.post('/bookmarks/toggle', dieuData)
  return response.data as { bookmarked: boolean }
}

export const getBookmarkStatus = async (mapc: string) => {
  const response = await apiClient.get(`/bookmarks/${encodeURIComponent(mapc)}/status`)
  return response.data as { bookmarked: boolean }
}

export const removeBookmark = async (mapc: string) => {
  const response = await apiClient.delete(`/bookmarks/${encodeURIComponent(mapc)}`)
  return response.data
}

// ── History API ───────────────────────────────────────────────────────────────

export const getHistory = async () => {
  const response = await apiClient.get('/history/')
  return response.data
}

export const addHistory = async (dieuData: Record<string, unknown>) => {
  const response = await apiClient.post('/history/', dieuData)
  return response.data
}

export const removeHistoryItem = async (mapc: string) => {
  const response = await apiClient.delete(`/history/${encodeURIComponent(mapc)}`)
  return response.data
}

export const clearHistory = async () => {
  const response = await apiClient.delete('/history/')
  return response.data
}

export default apiClient
