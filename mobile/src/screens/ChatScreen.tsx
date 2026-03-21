import React, { useEffect, useRef, useState } from 'react'
import {
  View, Text, StyleSheet, FlatList, KeyboardAvoidingView,
  Platform, TouchableOpacity, ActivityIndicator,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { sendMessage } from '../services/api'
import { useChatStore } from '../store/chatStore'
import { Colors } from '../theme/colors'
import MessageItem from '../components/MessageItem'
import InputArea from '../components/InputArea'
import ConversationDrawer from '../components/ConversationDrawer'
import { Message } from '../types'

export default function ChatScreen() {
  const {
    conversations, currentConversationId,
    fetchConversations, createConversation, deleteConversation,
    selectConversation, addMessage, updateTitle,
    isLoading: isChatLoading,
  } = useChatStore()

  const [sending, setSending] = useState(false)
  const [drawerOpen, setDrawerOpen] = useState(false)
  const listRef = useRef<FlatList>(null)

  const currentConversation = conversations.find((c) => c.id === currentConversationId) || null

  useEffect(() => {
    fetchConversations()
  }, [])

  useEffect(() => {
    if (conversations.length === 0 && !isChatLoading) {
      createConversation()
    }
  }, [conversations.length, isChatLoading])

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
      const response = await sendMessage(text, currentConversation.id, chuDeId)
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

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity style={styles.menuBtn} onPress={() => setDrawerOpen(true)}>
          <Text style={styles.menuBtnText}>☰</Text>
        </TouchableOpacity>
        <View style={styles.headerCenter}>
          <Text style={styles.headerEmoji}>⚖️</Text>
          <Text style={styles.headerTitle}>Tư vấn Pháp lý AI</Text>
        </View>
        <TouchableOpacity
          style={styles.newBtn}
          onPress={() => createConversation()}
          activeOpacity={0.7}
        >
          <Text style={styles.newBtnText}>✏</Text>
        </TouchableOpacity>
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
                <Text style={styles.emptyEmoji}>⚖️</Text>
                <Text style={styles.emptyTitle}>Hỏi về Luật Pháp Việt Nam</Text>
                <Text style={styles.emptyDesc}>
                  Trợ lý AI sẽ giúp bạn tìm hiểu về các vấn đề pháp lý dựa trên văn bản pháp luật chính thức.
                </Text>
                <View style={styles.hintRow}>
                  {['Tội trộm cắp bị phạt bao nhiêu?', 'Thủ tục đăng ký kết hôn'].map((q) => (
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
                  <Text style={styles.typingText}>⚖️ Đang trả lời...</Text>
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
  menuBtnText: { fontSize: 20, color: Colors.textMuted },
  headerCenter: { flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6 },
  headerEmoji: { fontSize: 20 },
  headerTitle: { fontSize: 15, fontWeight: '700', color: Colors.dark },
  newBtn: {
    width: 36,
    height: 36,
    alignItems: 'center',
    justifyContent: 'center',
  },
  newBtnText: { fontSize: 18, color: Colors.textMuted },

  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  loadingText: { marginTop: 12, color: Colors.textMuted, fontSize: 14 },

  empty: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32 },
  emptyEmoji: { fontSize: 52, marginBottom: 12 },
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
})
