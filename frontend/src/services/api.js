import axios from 'axios'
import { useAuthStore } from '../store/authStore'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
    'ngrok-skip-browser-warning': 'true',  // bypass ngrok warning page
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

export const updateProfile = async (data) => {
  const response = await apiClient.put('/auth/me', data)
  return response.data
}

export const uploadAvatar = async (file) => {
  const formData = new FormData()
  formData.append('file', file)
  const response = await apiClient.post('/auth/me/avatar', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return response.data
}

// ── Admin API ──────────────────────────────────────────────────────────────────

export const getAdminOverview    = async () => (await apiClient.get('/admin/stats/overview')).data
export const getAdminDaily       = async (days = 30) => (await apiClient.get('/admin/stats/daily', { params: { days } })).data
export const getAdminTopUsers    = async () => (await apiClient.get('/admin/stats/top-users')).data
export const getAdminTopBookmarks = async () => (await apiClient.get('/admin/stats/top-bookmarks')).data
export const getAdminTopViewed   = async () => (await apiClient.get('/admin/stats/top-viewed')).data
export const getAdminAllUsers    = async () => (await apiClient.get('/admin/users')).data
export const getAdminSettings    = async () => (await apiClient.get('/admin/settings')).data
export const updateGlobalDailyLimit = async (limit) => (await apiClient.put('/admin/settings/daily_limit', { limit })).data
export const setUserDailyLimit   = async (userId, limit) => (await apiClient.put(`/admin/users/${userId}/limit`, { limit })).data
export const resetUserDailyLimit  = async (userId) => (await apiClient.delete(`/admin/users/${userId}/limit`)).data
export const toggleUserActive     = async (userId) => (await apiClient.patch(`/admin/users/${userId}/toggle-active`)).data

// ── Payment / Subscription API ────────────────────────────────────────────────

export const getPlans            = async () => (await apiClient.get('/subscription/plans')).data
export const createPayment       = async (plan) => (await apiClient.post(`/subscription/create/${plan}`)).data
export const getMySubscription   = async () => (await apiClient.get('/subscription/my-subscription')).data
export const getMyTransactions   = async () => (await apiClient.get('/subscription/my-transactions')).data

// ── Quota API ──────────────────────────────────────────────────────────────────

export const getMyQuota = async () => (await apiClient.get('/quota')).data

export const changePassword = async (currentPassword, newPassword) => {
  const response = await apiClient.put('/auth/me/password', {
    current_password: currentPassword,
    new_password: newPassword,
  })
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

export const deleteConversation = async (conversationId) => {
  const response = await apiClient.delete(`/conversations/${conversationId}`)
  return response.data
}

// ── Roadmap API ──────────────────────────────────────────────────────────────

// Lấy lộ trình pháp lý ly hôn. Server trả đầy đủ cho Pro, teaser cho người khác.
export const getDivorceRoadmap = async () => {
  const response = await apiClient.get('/roadmap/divorce')
  return response.data
}

// Tải file mẫu đơn ly hôn (.docx) — chỉ Pro. Trả về Blob để trình duyệt lưu file.
export const downloadDivorceTemplate = async () => {
  const response = await apiClient.get('/roadmap/divorce/template', { responseType: 'blob' })
  return response.data
}

// ── Chat API ───────────────────────────────────────────────────────────────────

export const sendMessage = async (message, conversationId, chuDeId = null, module = null) => {
  try {
    const body = {
      query: message,
      conversation_id: conversationId ? String(conversationId) : undefined,
    }
    if (chuDeId) {
      body.chu_de_id = String(chuDeId)
    }
    if (module) {
      body.module = module
    }
    const response = await apiClient.post('/query', body)
    return response.data
  } catch (error) {
    console.error('API Error:', error)
    throw error
  }
}

/**
 * Stream a legal query answer via Server-Sent Events.
 * Uses fetch (not axios) so we can read the response body incrementally.
 *
 * handlers: { onSources(sources[]), onToken(text), onDone({model_used, usage}), onError({message}) }
 * Returns the parsed "done" payload, or throws on HTTP error (e.g. 429).
 */
export const streamMessage = async (message, conversationId, chuDeId = null, module = null, handlers = {}) => {
  const { onSources, onToken, onDone, onError } = handlers

  const body = {
    query: message,
    conversation_id: conversationId ? String(conversationId) : undefined,
  }
  if (chuDeId) body.chu_de_id = String(chuDeId)
  if (module) body.module = module

  const token = useAuthStore.getState().token
  const resp = await fetch(`${API_BASE_URL}/query/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'ngrok-skip-browser-warning': 'true',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  })

  if (!resp.ok) {
    if (resp.status === 401) useAuthStore.getState().logout()
    let detail
    try { detail = (await resp.json()).detail } catch { /* non-JSON body */ }
    const err = new Error('Stream request failed')
    err.status = resp.status
    err.detail = detail
    throw err
  }

  const reader = resp.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let donePayload = null

  const dispatch = (rawEvent) => {
    let event = 'message'
    const dataLines = []
    for (const line of rawEvent.split('\n')) {
      if (line.startsWith('event:')) event = line.slice(6).trim()
      else if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart())
    }
    if (dataLines.length === 0) return
    let parsed
    try { parsed = JSON.parse(dataLines.join('\n')) } catch { return }

    if (event === 'sources') onSources?.(parsed.sources || [])
    else if (event === 'token') onToken?.(parsed.text || '')
    else if (event === 'done') { donePayload = parsed; onDone?.(parsed) }
    else if (event === 'error') onError?.(parsed)
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    let sep
    while ((sep = buffer.indexOf('\n\n')) !== -1) {
      const rawEvent = buffer.slice(0, sep)
      buffer = buffer.slice(sep + 2)
      if (rawEvent.trim()) dispatch(rawEvent)
    }
  }
  // flush any trailing event without a final blank line
  if (buffer.trim()) dispatch(buffer)

  return donePayload
}

// ── Bookmark API ───────────────────────────────────────────────────────────────

export const getBookmarks = async () => {
  const response = await apiClient.get('/bookmarks/')
  return response.data
}

export const toggleBookmark = async (dieuData) => {
  const response = await apiClient.post('/bookmarks/toggle', dieuData)
  return response.data // { bookmarked: bool }
}

export const getBookmarkStatus = async (mapc) => {
  const response = await apiClient.get(`/bookmarks/${encodeURIComponent(mapc)}/status`)
  return response.data // { bookmarked: bool }
}

export const removeBookmark = async (mapc) => {
  const response = await apiClient.delete(`/bookmarks/${encodeURIComponent(mapc)}`)
  return response.data
}

// ── History API ────────────────────────────────────────────────────────────────

export const getHistory = async () => {
  const response = await apiClient.get('/history/')
  return response.data
}

export const addHistory = async (dieuData) => {
  const response = await apiClient.post('/history/', dieuData)
  return response.data
}

export const removeHistoryItem = async (mapc) => {
  const response = await apiClient.delete(`/history/${encodeURIComponent(mapc)}`)
  return response.data
}

export const clearHistory = async () => {
  const response = await apiClient.delete('/history/')
  return response.data
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

export const getDieuList = async ({ chuongId, demucId, mucId }) => {
  const params = {}
  if (chuongId) params.chuong_id = chuongId
  if (demucId) params.demuc_id = demucId
  if (mucId) params.muc_id = mucId
  const response = await apiClient.get('/law/dieu/list', { params })
  return response.data
}

export const getMuc = async (chuongId) => {
  const response = await apiClient.get('/law/muc', { params: { chuong_id: chuongId } })
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
