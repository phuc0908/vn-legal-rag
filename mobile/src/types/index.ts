// ── Auth ──────────────────────────────────────────────────────────────────────

export interface User {
  id: number
  username: string
  email?: string
  full_name?: string
  avatar_url?: string
  is_admin?: boolean
  subscription_plan?: 'free' | 'plus' | 'pro'
  subscription_expires_at?: string | null
}

export interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  setAuth: (user: User | null, token: string) => void
  logout: () => void
  updateUser: (user: User) => void
}

// ── Subscription / Payment ────────────────────────────────────────────────────

export interface Plan {
  id: string
  name: string
  amount: number
  days: number
  daily_limit: number
}

export interface Subscription {
  plan: 'free' | 'plus' | 'pro'
  expires_at: string | null
}

// ── Chat ──────────────────────────────────────────────────────────────────────

export interface SourceDocument {
  title: string
  content: string
  relevance_score: number
  metadata?: Record<string, string>
  url?: string
}

export interface Message {
  role: 'user' | 'assistant'
  content: string
  sources?: SourceDocument[]
}

export interface Conversation {
  id: string
  title: string
  messages: Message[]
  createdAt: string
}

export interface ChatState {
  conversations: Conversation[]
  currentConversationId: string | null
  isLoading: boolean
  fetchConversations: () => Promise<void>
  createConversation: (title?: string) => Promise<Conversation | null>
  deleteConversation: (id: string) => Promise<void>
  selectConversation: (id: string) => void
  addMessage: (conversationId: string, message: Message) => void
  updateTitle: (conversationId: string, title: string) => void
  clearHistory: () => void
}

// ── Law / Pháp điển ───────────────────────────────────────────────────────────

export interface Chude {
  id: number
  ten: string
  stt: number
}

export interface Demuc {
  id: number
  ten: string
  stt: number
}

export interface Chuong {
  mapc: string
  ten: string
  chimuc: string
  stt: number
}

export interface DieuItem {
  mapc: string
  ten: string
  chimuc: string
  stt: number
  vbqppl?: string
}

export interface DieuDetail extends DieuItem {
  noidung: string
  chude_ten?: string
  demuc_ten?: string
  chuong_ten?: string
  vbqppl_link?: string
  tables?: { id: number; html: string }[]
  related?: DieuItem[]
}

export interface LawStats {
  chude: number
  demuc: number
  chuong: number
  dieu: number
}

export interface SearchResult {
  mapc: string
  ten: string
  chimuc: string
  noidung_preview: string
  chude_ten: string
  demuc_ten: string
}

// ── Navigation ────────────────────────────────────────────────────────────────

export type RootStackParamList = {
  Main: undefined
  Login: undefined
  Register: undefined
  Profile: undefined
  Pricing: undefined
}

export type MainTabParamList = {
  HomeTab: undefined
  SearchTab: { q?: string }
  ChatTab: undefined
  LawTab: undefined
  SavedTab: undefined
}

// ── Bookmark / History ────────────────────────────────────────────────────────

export interface BookmarkItem {
  mapc: string
  ten: string
  chimuc: string
  chude_id?: number
  chude_ten?: string
  demuc_id?: number
  demuc_ten?: string
  chuong_id?: string
  chuong_ten?: string
  chuong_chimuc?: string
  vbqppl?: string
  created_at?: string
}

export interface HistoryItem extends BookmarkItem {
  viewed_at?: string
  viewedAt?: string
}

export type LawStackParamList = {
  LawBrowser: undefined
  DieuDetail: { mapc: string }
}
