import React from 'react'
import {
  View, Text, TouchableOpacity, StyleSheet, FlatList, Modal, Alert,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { Ionicons } from '@expo/vector-icons'
import { useAuthStore } from '../store/authStore'
import { Colors } from '../theme/colors'
import { Conversation } from '../types'

interface Props {
  visible: boolean
  onClose: () => void
  conversations: Conversation[]
  currentConversationId: string | null
  onNewChat: () => void
  onSelectChat: (id: string) => void
  onDeleteChat: (id: string) => void
}

export default function ConversationDrawer({
  visible, onClose, conversations, currentConversationId,
  onNewChat, onSelectChat, onDeleteChat,
}: Props) {
  const { user, logout } = useAuthStore()

  const getInitials = (name?: string) => {
    if (!name) return 'U'
    return name.split(' ').map((n) => n[0]).join('').toUpperCase().slice(0, 2)
  }

  const confirmDelete = (id: string, title: string) => {
    Alert.alert(
      'Xóa cuộc trò chuyện',
      `Bạn có chắc muốn xóa "${title}"?`,
      [
        { text: 'Hủy', style: 'cancel' },
        { text: 'Xóa', style: 'destructive', onPress: () => onDeleteChat(id) },
      ]
    )
  }

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent
      onRequestClose={onClose}
    >
      <View style={styles.overlay}>
        {/* Backdrop tap to close */}
        <TouchableOpacity style={styles.backdrop} activeOpacity={1} onPress={onClose} />

        {/* Drawer panel */}
        <SafeAreaView style={styles.drawer} edges={['top', 'bottom']}>
          {/* Logo */}
          <View style={styles.logo}>
            <Text style={styles.logoTitle}>Trợ lý Pháp lý</Text>
            <Text style={styles.logoSub}>Luật pháp Việt Nam</Text>
          </View>

          {/* New chat button */}
          <TouchableOpacity
            style={styles.newChatBtn}
            onPress={() => { onNewChat(); onClose() }}
            activeOpacity={0.8}
          >
            <Text style={styles.newChatText}>+ Cuộc trò chuyện mới</Text>
          </TouchableOpacity>

          {/* Conversations list */}
          {conversations.length > 0 && (
            <Text style={styles.sectionLabel}>Gần đây</Text>
          )}
          <FlatList
            data={conversations}
            keyExtractor={(item) => item.id}
            style={styles.list}
            renderItem={({ item }) => {
              const isActive = item.id === currentConversationId
              return (
                <TouchableOpacity
                  style={[styles.convItem, isActive && styles.convItemActive]}
                  onPress={() => { onSelectChat(item.id); onClose() }}
                  activeOpacity={0.7}
                >
                  <Text
                    style={[styles.convTitle, isActive && styles.convTitleActive]}
                    numberOfLines={1}
                  >
                    {item.title}
                  </Text>
                  <TouchableOpacity
                    style={styles.deleteBtn}
                    onPress={() => confirmDelete(item.id, item.title)}
                  >
                    <Text style={styles.deleteBtnText}>✕</Text>
                  </TouchableOpacity>
                </TouchableOpacity>
              )
            }}
          />

          {/* User profile footer */}
          <View style={styles.footer}>
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>
                {getInitials(user?.full_name || user?.username)}
              </Text>
            </View>
            <View style={styles.userInfo}>
              <Text style={styles.userName} numberOfLines={1}>
                {user?.full_name || user?.username || 'Người dùng'}
              </Text>
              <Text style={styles.userEmail} numberOfLines={1}>
                {user?.email || 'Chưa cập nhật email'}
              </Text>
            </View>
            <TouchableOpacity
              style={styles.logoutBtn}
              onPress={() => {
                Alert.alert('Đăng xuất', 'Bạn có chắc muốn đăng xuất?', [
                  { text: 'Hủy', style: 'cancel' },
                  { text: 'Đăng xuất', style: 'destructive', onPress: logout },
                ])
              }}
            >
              <Ionicons name="log-out-outline" size={18} color="rgba(255,255,255,0.7)" />
            </TouchableOpacity>
          </View>
        </SafeAreaView>
      </View>
    </Modal>
  )
}

const DRAWER_WIDTH = 300

const styles = StyleSheet.create({
  overlay: { flex: 1, flexDirection: 'row' },
  backdrop: { flex: 1, backgroundColor: 'rgba(0,0,0,0.4)' },

  drawer: {
    width: DRAWER_WIDTH,
    backgroundColor: Colors.dark,
    paddingTop: 0,
  },

  logo: {
    padding: 20,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255,255,255,0.1)',
  },
  logoTitle: { fontSize: 18, fontWeight: '800', color: '#fff' },
  logoSub: { fontSize: 11, color: 'rgba(255,255,255,0.5)', marginTop: 2 },

  newChatBtn: {
    margin: 12,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.2)',
    borderRadius: 8,
    paddingVertical: 10,
    alignItems: 'center',
  },
  newChatText: { color: '#fff', fontSize: 14, fontWeight: '600' },

  sectionLabel: {
    fontSize: 11,
    fontWeight: '700',
    color: 'rgba(255,255,255,0.4)',
    paddingHorizontal: 16,
    paddingBottom: 6,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },

  list: { flex: 1 },

  convItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 14,
    paddingVertical: 10,
    borderRadius: 8,
    marginHorizontal: 8,
    marginBottom: 2,
  },
  convItemActive: { backgroundColor: 'rgba(192,57,43,0.35)' },
  convTitle: { flex: 1, fontSize: 13, color: 'rgba(255,255,255,0.75)' },
  convTitleActive: { color: '#fff', fontWeight: '600' },
  deleteBtn: { padding: 4 },
  deleteBtnText: { fontSize: 11, color: 'rgba(255,255,255,0.4)' },

  footer: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 14,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255,255,255,0.1)',
    gap: 10,
  },
  avatar: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: Colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  avatarText: { color: '#fff', fontWeight: '700', fontSize: 14 },
  userInfo: { flex: 1 },
  userName: { fontSize: 13, fontWeight: '600', color: '#fff' },
  userEmail: { fontSize: 11, color: 'rgba(255,255,255,0.5)', marginTop: 1 },
  logoutBtn: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: 'rgba(255,255,255,0.1)',
    alignItems: 'center',
    justifyContent: 'center',
  },
})
