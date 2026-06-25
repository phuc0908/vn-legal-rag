import React, { useEffect, useRef, useState } from 'react'
import {
  View, Text, StyleSheet, FlatList, KeyboardAvoidingView,
  Platform, TouchableOpacity, ActivityIndicator,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { useNavigation } from '@react-navigation/native'
import { NativeStackNavigationProp } from '@react-navigation/native-stack'
import { Ionicons } from '@expo/vector-icons'
import { sendMessage } from '../services/api'
import { useChatStore } from '../store/chatStore'
import { useAuthStore } from '../store/authStore'
import { Colors } from '../theme/colors'
import MessageItem from '../components/MessageItem'
import InputArea from '../components/InputArea'
import ConversationDrawer from '../components/ConversationDrawer'
import { Message, RootStackParamList } from '../types'

const MODULES = [
  { key: null, label: 'Tất cả' },
  { key: 'hon_nhan', label: 'Hôn nhân' },
]

const MODULE_HINTS: Record<string, string[]> = {
  all: ['Tội trộm cắp bị phạt bao nhiêu?', 'Thủ tục đăng ký kết hôn'],
  hon_nhan: ['Thủ tục ly hôn đơn phương', 'Chia tài sản sau khi ly hôn'],
}

export default function ChatScreen() {
  const { isAuthenticated } = useAuthStore()
  const navigation = useNavigation<NativeStackNavigationProp<RootStackParamList>>()
  const {
    conversations, currentConversationId,
    fetchConversations, createConversation, deleteConversation,
    selectConversation, addMessage, updateTitle,
    isLoading: isChatLoading,
  } = useChatStore()

  const [sending, setSending] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [selectedModule, setSelectedModule] = useState<string | null>(null)
  const listRef = useRef<FlatList>(null)

  const currentConversation = conversations.find((c) => c.id === currentConversationId) || null

  useEffect(() => {
    if (isAuthenticated) fetchConversations()
  }, [isAuthenticated])

  useEffect(() => {
    if (isAuthenticated && conversations.length === 0 && !isChatLoading) {
      createConversation()
    }
  }, [isAuthenticated, conversations.length, isChatLoading])

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    if (currentConversation?.messages?.length) {
      setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 100)
    }
  }, [currentConversation?.messages?.length])

  const handleSend = async (text: string, chuDeId: string | null) => {
    if (!currentConversation) return

    if (currentConversation.messages.length === 0) {
      updateTitle(currentConversation.id, text.substring(0, 45))
    }

    const userMsg: Message = { role: 'user', content: text }
    addMessage(currentConversation.id, userMsg)
    setSending(true)

    try {
      const response = await sendMessage(text, currentConversation.id, chuDeId, selectedModule)
      addMessage(currentConversation.id, {
        role: 'assistant',
        content: response.answer,
        sources: response.sources,
      })
    } catch {
      addMessage(currentConversation.id, {
        role: 'assistant',
        content: 'Xin lỗi, có lỗi xảy ra. Vui lòng kiểm tra kết nối và thử lại.',
      })
    } finally {
      setSending(false)
    }
  }

  const messages = currentConversation?.messages || []

  if (!isAuthenticated) {
    return (
      <SafeAreaView style={styles.safe} edges={['top']}>
        <View style={styles.authGate}>
          <Ionicons name="shield-checkmark-outline" size={56} color={Colors.primary} style={{ marginBottom: 16 }} />
          <Text style={styles.authTitle}>Đăng nhập để Tư vấn AI</Text>
          <Text style={styles.authDesc}>
            Tính năng tư vấn pháp lý AI yêu cầu đăng nhập để lưu lịch sử trò chuyện.
          </Text>
          <TouchableOpacity style={styles.loginBtn} onPress={() => navigation.navigate('Login')}>
            <Text style={styles.loginBtnText}>Đăng nhập</Text>
          </TouchableOpacity>
          <TouchableOpacity onPress={() => navigation.navigate('Register')}>
            <Text style={styles.registerLink}>Chưa có tài khoản? Đăng ký</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    )
  }

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity style={styles.menuBtn} onPress={() => setDrawerOpen(true)}>
          <Ionicons name="menu-outline" size={24} color={Colors.textMuted} />
        </TouchableOpacity>
        <View style={styles.headerCenter}>
          <Text style={styles.headerTitle}>Tư vấn Pháp lý AI</Text>
        </View>
        <TouchableOpacity
          style={styles.newBtn}
          onPress={() => createConversation()}
          activeOpacity={0.7}
        >
          <Ionicons name="create-outline" size={22} color={Colors.textMuted} />
        </TouchableOpacity>
      </View>

      {/* Module Tab Strip */}
      <View style={styles.moduleTabs}>
        {MODULES.map((m) => {
          const active = selectedModule === m.key
          return (
            <TouchableOpacity
              key={String(m.key)}
              style={[styles.moduleTab, active && styles.moduleTabActive]}
              onPress={() => setSelectedModule(m.key)}
              activeOpacity={0.7}
            >
              <Text style={[styles.moduleTabText, active && styles.moduleTabTextActive]}>
                {m.label}
              </Text>
            </TouchableOpacity>
          )
        })}
      </View>

      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 0 : 0}
      >
        {isChatLoading ? (
          <View style={styles.center}>
            <ActivityIndicator size="large" color={Colors.primary} />
            <Text style={styles.loadingText}>Đang tải lịch sử trò chuyện...</Text>
          </View>
        ) : (
          <>
            {/* Messages */}
            {messages.length === 0 ? (
              <View style={styles.empty}>
                <Ionicons name="chatbubbles-outline" size={52} color={Colors.border} style={{ marginBottom: 12 }} />
                <Text style={styles.emptyTitle}>Hỏi về Luật Pháp Việt Nam</Text>
                <Text style={styles.emptyDesc}>
                  Trợ lý AI sẽ giúp bạn tìm hiểu về các vấn đề pháp lý dựa trên văn bản pháp luật chính thức.
                </Text>
                <View style={styles.hintRow}>
                  {(MODULE_HINTS[selectedModule ?? 'all'] ?? MODULE_HINTS.all).map((q) => (
                    <TouchableOpacity
                      key={q}
                      style={styles.hintTag}
                      onPress={() => handleSend(q, null)}
                    >
                      <Text style={styles.hintTagText}>{q}</Text>
                    </TouchableOpacity>
                  ))}
                </View>
              </View>
            ) : (
              <FlatList
                ref={listRef}
                data={messages}
                keyExtractor={(_, idx) => String(idx)}
                renderItem={({ item }) => <MessageItem message={item} />}
                contentContainerStyle={styles.messagesList}
                showsVerticalScrollIndicator={false}
                onContentSizeChange={() =>
                  listRef.current?.scrollToEnd({ animated: false })
                }
              />
            )}

            {/* Typing indicator */}
            {sending && (
              <View style={styles.typingRow}>
                <View style={styles.typingBubble}>
                  <Text style={styles.typingText}>Đang trả lời...</Text>
                  <ActivityIndicator size="small" color={Colors.textMuted} style={{ marginLeft: 6 }} />
                </View>
              </View>
            )}

            {/* Input area */}
            <InputArea onSend={handleSend} loading={sending} disabled={!currentConversation} />
          </>
        )}
      </KeyboardAvoidingView>

      {/* Conversations Drawer */}
      <ConversationDrawer
        visible={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        conversations={conversations}
        currentConversationId={currentConversationId}
        onNewChat={createConversation}
        onSelectChat={selectConversation}
        onDeleteChat={deleteConversation}
      />
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.background },
  flex: { flex: 1 },

  header: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderBottomWidth: 2,
    borderBottomColor: Colors.primary,
    gap: 8,
  },
  menuBtn: {
    width: 36,
    height: 36,
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerCenter: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  headerTitle: { fontSize: 15, fontWeight: '700', color: Colors.dark },
  newBtn: { width: 36, height: 36, alignItems: 'center', justifyContent: 'center' },

  moduleTabs: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
    gap: 8,
  },
  moduleTab: {
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: Colors.borderDark,
    backgroundColor: Colors.inputBg,
  },
  moduleTabActive: {
    backgroundColor: Colors.primary,
    borderColor: Colors.primary,
  },
  moduleTabText: { fontSize: 13, color: Colors.textSecondary, fontWeight: '500' },
  moduleTabTextActive: { color: '#fff', fontWeight: '700' },

  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  loadingText: { marginTop: 12, color: Colors.textMuted, fontSize: 14 },

  empty: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32 },
  emptyTitle: { fontSize: 20, fontWeight: '800', color: Colors.dark, marginBottom: 8, textAlign: 'center' },
  emptyDesc: { fontSize: 13, color: Colors.textMuted, textAlign: 'center', lineHeight: 18, marginBottom: 20 },
  hintRow: { gap: 8, alignItems: 'stretch', width: '100%' },
  hintTag: {
    backgroundColor: Colors.cardBg,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: Colors.border,
    padding: 12,
  },
  hintTagText: { fontSize: 13, color: Colors.text, textAlign: 'center' },

  messagesList: { paddingTop: 12, paddingBottom: 8 },

  typingRow: { paddingHorizontal: 12, paddingBottom: 4 },
  typingBubble: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.cardBg,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: Colors.border,
    paddingHorizontal: 12,
    paddingVertical: 8,
    alignSelf: 'flex-start',
  },
  typingText: { fontSize: 13, color: Colors.textMuted, fontStyle: 'italic' },

  authGate: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32 },
  authTitle: { fontSize: 20, fontWeight: '800', color: Colors.dark, marginBottom: 10, textAlign: 'center' },
  authDesc: { fontSize: 14, color: Colors.textMuted, textAlign: 'center', lineHeight: 20, marginBottom: 28 },
  loginBtn: {
    backgroundColor: Colors.primary,
    borderRadius: 10,
    paddingVertical: 14,
    paddingHorizontal: 40,
    marginBottom: 14,
    width: '100%',
    alignItems: 'center',
  },
  loginBtnText: { color: '#fff', fontSize: 15, fontWeight: '700' },
  registerLink: { fontSize: 14, color: Colors.primary, fontWeight: '600' },
})
