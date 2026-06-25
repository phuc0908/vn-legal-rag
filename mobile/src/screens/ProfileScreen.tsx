import React, { useState, useEffect } from 'react'
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  ScrollView, ActivityIndicator, Alert, Image, Modal,
} from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { SafeAreaView } from 'react-native-safe-area-context'
import { useNavigation } from '@react-navigation/native'
import { NativeStackNavigationProp } from '@react-navigation/native-stack'
import { useAuthStore } from '../store/authStore'
import { getMe, updateProfile, changePassword, getMySubscription, getBookmarks, getHistory } from '../services/api'
import { Colors } from '../theme/colors'
import { RootStackParamList } from '../types'

type NavProp = NativeStackNavigationProp<RootStackParamList>

const PLAN_LABELS: Record<string, string> = { free: 'Miễn phí', plus: 'Plus', pro: 'Pro' }
const PLAN_COLORS: Record<string, string> = { free: '#6b7280', plus: '#2980b9', pro: '#f39c12' }

export default function ProfileScreen() {
  const navigation = useNavigation<NavProp>()
  const { user, logout, updateUser } = useAuthStore()

  const [fullName, setFullName] = useState(user?.full_name ?? '')
  const [email, setEmail] = useState(user?.email ?? '')
  const [editMode, setEditMode] = useState(false)
  const [savingProfile, setSavingProfile] = useState(false)

  const [pwdModal, setPwdModal] = useState(false)
  const [currentPwd, setCurrentPwd] = useState('')
  const [newPwd, setNewPwd] = useState('')
  const [confirmPwd, setConfirmPwd] = useState('')
  const [savingPwd, setSavingPwd] = useState(false)

  const [subscription, setSubscription] = useState<{ plan: string; expires_at: string | null } | null>(null)
  const [bookmarkCount, setBookmarkCount] = useState<number | null>(null)
  const [historyCount, setHistoryCount] = useState<number | null>(null)

  useEffect(() => {
    // Refresh user info
    getMe()
      .then((u) => { updateUser(u); setFullName(u.full_name ?? ''); setEmail(u.email ?? '') })
      .catch(() => {})
    getMySubscription().then(setSubscription).catch(() => {})
    getBookmarks().then((b) => setBookmarkCount(Array.isArray(b) ? b.length : 0)).catch(() => {})
    getHistory().then((h) => setHistoryCount(Array.isArray(h) ? h.length : 0)).catch(() => {})
  }, [])

  const handleSaveProfile = async () => {
    setSavingProfile(true)
    try {
      const updated = await updateProfile({ full_name: fullName.trim() || undefined, email: email.trim() || undefined })
      updateUser(updated)
      setEditMode(false)
      Alert.alert('Thành công', 'Đã cập nhật hồ sơ.')
    } catch (err: any) {
      Alert.alert('Lỗi', err.response?.data?.detail || 'Không thể cập nhật hồ sơ.')
    } finally {
      setSavingProfile(false)
    }
  }

  const handleChangePassword = async () => {
    if (!currentPwd || !newPwd || !confirmPwd) {
      Alert.alert('Lỗi', 'Vui lòng điền đầy đủ các trường.')
      return
    }
    if (newPwd !== confirmPwd) {
      Alert.alert('Lỗi', 'Mật khẩu mới không khớp.')
      return
    }
    if (newPwd.length < 6) {
      Alert.alert('Lỗi', 'Mật khẩu mới phải có ít nhất 6 ký tự.')
      return
    }
    setSavingPwd(true)
    try {
      await changePassword(currentPwd, newPwd)
      setPwdModal(false)
      setCurrentPwd(''); setNewPwd(''); setConfirmPwd('')
      Alert.alert('Thành công', 'Đã đổi mật khẩu.')
    } catch (err: any) {
      Alert.alert('Lỗi', err.response?.data?.detail || 'Mật khẩu hiện tại không đúng.')
    } finally {
      setSavingPwd(false)
    }
  }

  const handleLogout = () => {
    Alert.alert('Đăng xuất', 'Bạn có chắc muốn đăng xuất?', [
      { text: 'Hủy', style: 'cancel' },
      { text: 'Đăng xuất', style: 'destructive', onPress: () => { logout(); navigation.goBack() } },
    ])
  }

  const plan = subscription?.plan ?? user?.subscription_plan ?? 'free'
  const planColor = PLAN_COLORS[plan] ?? PLAN_COLORS.free
  const planLabel = PLAN_LABELS[plan] ?? plan

  const initials = (user?.full_name || user?.username || '?')
    .split(' ')
    .map((w) => w[0])
    .slice(0, 2)
    .join('')
    .toUpperCase()

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
          <Text style={styles.backText}>← Quay lại</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Tài khoản</Text>
        <View style={{ width: 70 }} />
      </View>

      <ScrollView contentContainerStyle={styles.container} showsVerticalScrollIndicator={false}>
        {/* Avatar + Name */}
        <View style={styles.avatarSection}>
          {user?.avatar_url ? (
            <Image source={{ uri: user.avatar_url }} style={styles.avatar} />
          ) : (
            <View style={[styles.avatar, styles.avatarFallback]}>
              <Text style={styles.avatarInitials}>{initials}</Text>
            </View>
          )}
          <Text style={styles.username}>@{user?.username}</Text>
          <View style={[styles.planBadge, { backgroundColor: planColor }]}>
            <Text style={styles.planBadgeText}>{planLabel}</Text>
          </View>
        </View>

        {/* Stats */}
        <View style={styles.statsRow}>
          <View style={styles.statBox}>
            <Text style={styles.statNum}>{bookmarkCount ?? '—'}</Text>
            <Text style={styles.statLabel}>Đã lưu</Text>
          </View>
          <View style={styles.statDivider} />
          <View style={styles.statBox}>
            <Text style={styles.statNum}>{historyCount ?? '—'}</Text>
            <Text style={styles.statLabel}>Đã xem</Text>
          </View>
          {subscription?.expires_at && (
            <>
              <View style={styles.statDivider} />
              <View style={styles.statBox}>
                <Text style={styles.statNum} numberOfLines={1}>
                  {new Date(subscription.expires_at).toLocaleDateString('vi-VN')}
                </Text>
                <Text style={styles.statLabel}>Hết hạn</Text>
              </View>
            </>
          )}
        </View>

        {/* Profile Fields */}
        <View style={styles.card}>
          <View style={styles.cardHeader}>
            <Text style={styles.cardTitle}>Thông tin cá nhân</Text>
            {!editMode ? (
              <TouchableOpacity onPress={() => setEditMode(true)}>
                <Text style={styles.editBtn}>Chỉnh sửa</Text>
              </TouchableOpacity>
            ) : (
              <TouchableOpacity onPress={() => { setEditMode(false); setFullName(user?.full_name ?? ''); setEmail(user?.email ?? '') }}>
                <Text style={styles.cancelBtn}>Hủy</Text>
              </TouchableOpacity>
            )}
          </View>

          <Text style={styles.fieldLabel}>Tên đăng nhập</Text>
          <View style={styles.fieldReadonly}>
            <Text style={styles.fieldReadonlyText}>{user?.username}</Text>
          </View>

          <Text style={styles.fieldLabel}>Họ và tên</Text>
          {editMode ? (
            <TextInput
              style={styles.fieldInput}
              value={fullName}
              onChangeText={setFullName}
              placeholder="Nhập họ và tên"
              placeholderTextColor={Colors.textPlaceholder}
            />
          ) : (
            <View style={styles.fieldReadonly}>
              <Text style={styles.fieldReadonlyText}>{user?.full_name || '—'}</Text>
            </View>
          )}

          <Text style={styles.fieldLabel}>Email</Text>
          {editMode ? (
            <TextInput
              style={styles.fieldInput}
              value={email}
              onChangeText={setEmail}
              placeholder="Nhập email"
              placeholderTextColor={Colors.textPlaceholder}
              keyboardType="email-address"
              autoCapitalize="none"
            />
          ) : (
            <View style={styles.fieldReadonly}>
              <Text style={styles.fieldReadonlyText}>{user?.email || '—'}</Text>
            </View>
          )}

          {editMode && (
            <TouchableOpacity
              style={[styles.saveBtn, savingProfile && { opacity: 0.7 }]}
              onPress={handleSaveProfile}
              disabled={savingProfile}
            >
              {savingProfile ? <ActivityIndicator color="#fff" /> : <Text style={styles.saveBtnText}>Lưu thay đổi</Text>}
            </TouchableOpacity>
          )}
        </View>

        {/* Security */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Bảo mật</Text>
          <TouchableOpacity style={styles.actionRow} onPress={() => setPwdModal(true)}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
              <Ionicons name="key-outline" size={18} color={Colors.textSecondary} />
              <Text style={styles.actionRowText}>Đổi mật khẩu</Text>
            </View>
            <Text style={styles.actionRowArrow}>›</Text>
          </TouchableOpacity>
        </View>

        {/* Subscription */}
        <View style={styles.card}>
          <Text style={styles.cardTitle}>Gói dịch vụ</Text>
          <View style={styles.subRow}>
            <View style={[styles.planBadgeLarge, { backgroundColor: planColor }]}>
              <Text style={styles.planBadgeLargeText}>{planLabel}</Text>
            </View>
            <Text style={styles.subDesc}>
              {plan === 'free'
                ? 'Gói miễn phí – 20 câu hỏi/ngày'
                : plan === 'plus'
                ? 'Gói Plus – 100 câu hỏi/ngày'
                : 'Gói Pro – Không giới hạn'}
            </Text>
          </View>
          {plan === 'free' && (
            <TouchableOpacity
              style={styles.upgradeBtn}
              onPress={() => navigation.navigate('Pricing')}
            >
              <Text style={styles.upgradeBtnText}>Nâng cấp gói</Text>
            </TouchableOpacity>
          )}
          {plan !== 'free' && (
            <TouchableOpacity
              style={[styles.upgradeBtn, { backgroundColor: '#f0f4ff' }]}
              onPress={() => navigation.navigate('Pricing')}
            >
              <Text style={[styles.upgradeBtnText, { color: Colors.primary }]}>Xem các gói dịch vụ</Text>
            </TouchableOpacity>
          )}
        </View>

        {/* Logout */}
        <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout}>
          <Text style={styles.logoutBtnText}>Đăng xuất</Text>
        </TouchableOpacity>
      </ScrollView>

      {/* Change Password Modal */}
      <Modal visible={pwdModal} animationType="slide" transparent onRequestClose={() => setPwdModal(false)}>
        <TouchableOpacity style={styles.modalOverlay} activeOpacity={1} onPress={() => setPwdModal(false)}>
          <TouchableOpacity activeOpacity={1} style={styles.modalSheet}>
            <View style={styles.modalHandle} />
            <Text style={styles.modalTitle}>Đổi mật khẩu</Text>

            <Text style={styles.fieldLabel}>Mật khẩu hiện tại</Text>
            <TextInput
              style={styles.fieldInput}
              value={currentPwd}
              onChangeText={setCurrentPwd}
              placeholder="Nhập mật khẩu hiện tại"
              placeholderTextColor={Colors.textPlaceholder}
              secureTextEntry
            />

            <Text style={styles.fieldLabel}>Mật khẩu mới</Text>
            <TextInput
              style={styles.fieldInput}
              value={newPwd}
              onChangeText={setNewPwd}
              placeholder="Ít nhất 6 ký tự"
              placeholderTextColor={Colors.textPlaceholder}
              secureTextEntry
            />

            <Text style={styles.fieldLabel}>Xác nhận mật khẩu mới</Text>
            <TextInput
              style={styles.fieldInput}
              value={confirmPwd}
              onChangeText={setConfirmPwd}
              placeholder="Nhập lại mật khẩu mới"
              placeholderTextColor={Colors.textPlaceholder}
              secureTextEntry
            />

            <TouchableOpacity
              style={[styles.saveBtn, savingPwd && { opacity: 0.7 }]}
              onPress={handleChangePassword}
              disabled={savingPwd}
            >
              {savingPwd ? <ActivityIndicator color="#fff" /> : <Text style={styles.saveBtnText}>Xác nhận đổi mật khẩu</Text>}
            </TouchableOpacity>
          </TouchableOpacity>
        </TouchableOpacity>
      </Modal>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.background },

  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    backgroundColor: '#fff',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  backBtn: { minWidth: 70 },
  backText: { fontSize: 14, color: Colors.primary, fontWeight: '600' },
  headerTitle: { fontSize: 16, fontWeight: '800', color: Colors.dark },

  container: { padding: 16, gap: 16, paddingBottom: 40 },

  avatarSection: { alignItems: 'center', paddingVertical: 8 },
  avatar: { width: 80, height: 80, borderRadius: 40, marginBottom: 10 },
  avatarFallback: {
    backgroundColor: Colors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarInitials: { fontSize: 30, fontWeight: '800', color: '#fff' },
  username: { fontSize: 15, color: Colors.textMuted, marginBottom: 8 },
  planBadge: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 20,
  },
  planBadgeText: { color: '#fff', fontSize: 12, fontWeight: '700' },

  statsRow: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
  },
  statBox: { flex: 1, alignItems: 'center' },
  statNum: { fontSize: 18, fontWeight: '800', color: Colors.dark },
  statLabel: { fontSize: 11, color: Colors.textMuted, marginTop: 2 },
  statDivider: { width: 1, height: 32, backgroundColor: Colors.border },

  card: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 4,
    elevation: 2,
    gap: 8,
  },
  cardHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  cardTitle: { fontSize: 14, fontWeight: '700', color: Colors.dark },
  editBtn: { fontSize: 13, color: Colors.primary, fontWeight: '600' },
  cancelBtn: { fontSize: 13, color: Colors.textMuted },

  fieldLabel: { fontSize: 12, fontWeight: '600', color: Colors.textSecondary },
  fieldReadonly: {
    backgroundColor: Colors.inputBg,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  fieldReadonlyText: { fontSize: 14, color: Colors.text },
  fieldInput: {
    borderWidth: 1,
    borderColor: Colors.borderDark,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 10,
    fontSize: 14,
    color: Colors.text,
    backgroundColor: Colors.inputBg,
  },
  saveBtn: {
    backgroundColor: Colors.primary,
    borderRadius: 10,
    paddingVertical: 13,
    alignItems: 'center',
    marginTop: 4,
  },
  saveBtnText: { color: '#fff', fontSize: 14, fontWeight: '700' },

  actionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingVertical: 10,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
    marginTop: 4,
  },
  actionRowText: { fontSize: 14, color: Colors.text },
  actionRowArrow: { fontSize: 20, color: Colors.textMuted },

  subRow: { flexDirection: 'row', alignItems: 'center', gap: 12, marginTop: 4 },
  planBadgeLarge: { paddingHorizontal: 14, paddingVertical: 6, borderRadius: 20 },
  planBadgeLargeText: { color: '#fff', fontSize: 13, fontWeight: '700' },
  subDesc: { fontSize: 13, color: Colors.textSecondary, flex: 1 },
  upgradeBtn: {
    backgroundColor: Colors.primary,
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: 'center',
    marginTop: 8,
  },
  upgradeBtnText: { color: '#fff', fontSize: 14, fontWeight: '700' },

  logoutBtn: {
    borderWidth: 1.5,
    borderColor: Colors.error,
    borderRadius: 10,
    paddingVertical: 13,
    alignItems: 'center',
    marginTop: 4,
  },
  logoutBtnText: { color: Colors.error, fontSize: 14, fontWeight: '700' },

  // Password modal
  modalOverlay: { flex: 1, backgroundColor: 'rgba(0,0,0,0.4)', justifyContent: 'flex-end' },
  modalSheet: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    padding: 20,
    paddingBottom: 36,
    gap: 8,
  },
  modalHandle: {
    width: 40, height: 4, backgroundColor: Colors.border,
    borderRadius: 2, alignSelf: 'center', marginBottom: 12,
  },
  modalTitle: { fontSize: 16, fontWeight: '800', color: Colors.dark, marginBottom: 4 },
})
