import React, { useState, useEffect, useCallback } from 'react'
import {
  View, Text, TouchableOpacity, StyleSheet,
  FlatList, ActivityIndicator, Alert,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { useNavigation } from '@react-navigation/native'
import { NativeStackNavigationProp } from '@react-navigation/native-stack'
import {
  getBookmarks, removeBookmark,
  getHistory, removeHistoryItem, clearHistory,
} from '../services/api'
import { useAuthStore } from '../store/authStore'
import { Colors } from '../theme/colors'
import { BookmarkItem, HistoryItem, RootStackParamList } from '../types'

type NavProp = NativeStackNavigationProp<RootStackParamList>

function DieuCard({
  item,
  type,
  onRemove,
  onNavigate,
}: {
  item: BookmarkItem | HistoryItem
  type: 'bookmark' | 'history'
  onRemove: (mapc: string) => void
  onNavigate: (mapc: string) => void
}) {
  const dateStr = type === 'bookmark'
    ? (item as BookmarkItem).created_at
    : (item as HistoryItem).viewed_at || (item as HistoryItem).viewedAt

  return (
    <TouchableOpacity style={styles.card} onPress={() => onNavigate(item.mapc)} activeOpacity={0.75}>
      {/* Breadcrumb */}
      <View style={styles.breadcrumb}>
        {item.chude_ten && <Text style={styles.bcText} numberOfLines={1}>{item.chude_ten}</Text>}
        {item.demuc_ten && (
          <>
            <Text style={styles.bcSep}>›</Text>
            <Text style={styles.bcText} numberOfLines={1}>{item.demuc_ten}</Text>
          </>
        )}
        {item.chuong_ten && (
          <>
            <Text style={styles.bcSep}>›</Text>
            <Text style={styles.bcText} numberOfLines={1}>
              {item.chuong_chimuc ? `Chương ${item.chuong_chimuc}` : item.chuong_ten}
            </Text>
          </>
        )}
      </View>

      {/* Title row */}
      <View style={styles.cardMain}>
        <View style={styles.cardTitleWrap}>
          <Text style={styles.cardNum}>Điều {item.chimuc}</Text>
          <Text style={styles.cardTitle} numberOfLines={2}>{item.ten}</Text>
          {item.vbqppl ? <Text style={styles.cardVb} numberOfLines={1}>{item.vbqppl}</Text> : null}
        </View>
      </View>

      {/* Footer */}
      <View style={styles.cardFooter}>
        {dateStr ? (
          <Text style={styles.cardDate}>
            {type === 'bookmark' ? 'Lưu lúc ' : 'Xem lúc '}
            {new Date(dateStr).toLocaleString('vi-VN', { dateStyle: 'short', timeStyle: 'short' })}
          </Text>
        ) : <View />}
        <TouchableOpacity
          style={styles.removeBtn}
          onPress={() => onRemove(item.mapc)}
          hitSlop={{ top: 8, bottom: 8, left: 8, right: 8 }}
        >
          <Text style={styles.removeBtnText}>Xóa</Text>
        </TouchableOpacity>
      </View>
    </TouchableOpacity>
  )
}

export default function SavedScreen() {
  const navigation = useNavigation<NavProp>()
  const { isAuthenticated } = useAuthStore()
  const [tab, setTab] = useState<'bookmarks' | 'history'>('bookmarks')

  const [bookmarks, setBookmarks] = useState<BookmarkItem[]>([])
  const [bookmarkLoading, setBookmarkLoading] = useState(false)
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)

  const loadBookmarks = useCallback(async () => {
    if (!isAuthenticated) return
    setBookmarkLoading(true)
    try {
      const data = await getBookmarks()
      setBookmarks(data)
    } catch {}
    finally { setBookmarkLoading(false) }
  }, [isAuthenticated])

  const loadHistory = useCallback(async () => {
    if (!isAuthenticated) return
    setHistoryLoading(true)
    try {
      const data = await getHistory()
      setHistory(data.map((h: HistoryItem) => ({ ...h, viewedAt: h.viewed_at })))
    } catch {}
    finally { setHistoryLoading(false) }
  }, [isAuthenticated])

  useEffect(() => {
    if (tab === 'bookmarks') loadBookmarks()
    else loadHistory()
  }, [tab, isAuthenticated])

  const handleRemoveBookmark = async (mapc: string) => {
    try {
      await removeBookmark(mapc)
      setBookmarks(prev => prev.filter(b => b.mapc !== mapc))
    } catch {}
  }

  const handleRemoveHistory = async (mapc: string) => {
    try {
      await removeHistoryItem(mapc)
      setHistory(prev => prev.filter(h => h.mapc !== mapc))
    } catch {}
  }

  const handleClearHistory = () => {
    Alert.alert(
      'Xóa lịch sử',
      'Bạn có chắc muốn xóa toàn bộ lịch sử xem?',
      [
        { text: 'Hủy', style: 'cancel' },
        {
          text: 'Xóa tất cả',
          style: 'destructive',
          onPress: async () => {
            try {
              await clearHistory()
              setHistory([])
            } catch {}
          },
        },
      ]
    )
  }

  const navigateToDieu = (mapc: string) => {
    // @ts-ignore
    navigation.navigate('Main', {
      screen: 'LawTab',
      params: { screen: 'DieuDetail', params: { mapc } },
    })
  }

  const AuthRequired = ({ msg }: { msg: string }) => (
    <View style={styles.emptyBox}>
      <Text style={styles.emptyEmoji}>🔒</Text>
      <Text style={styles.emptyTitle}>Cần đăng nhập</Text>
      <Text style={styles.emptyDesc}>{msg}</Text>
      <TouchableOpacity
        style={styles.ctaBtn}
        // @ts-ignore
        onPress={() => navigation.navigate('Login')}
      >
        <Text style={styles.ctaBtnText}>Đăng nhập ngay</Text>
      </TouchableOpacity>
    </View>
  )

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>📚 Thư viện của tôi</Text>
        <Text style={styles.headerSub}>Điều luật đã lưu và lịch sử xem</Text>
      </View>

      {/* Tabs */}
      <View style={styles.tabs}>
        <TouchableOpacity
          style={[styles.tab, tab === 'bookmarks' && styles.tabActive]}
          onPress={() => setTab('bookmarks')}
        >
          <Text style={[styles.tabText, tab === 'bookmarks' && styles.tabTextActive]}>
            ★ Đã lưu{bookmarks.length > 0 ? ` (${bookmarks.length})` : ''}
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          style={[styles.tab, tab === 'history' && styles.tabActive]}
          onPress={() => setTab('history')}
        >
          <Text style={[styles.tabText, tab === 'history' && styles.tabTextActive]}>
            🕐 Lịch sử{history.length > 0 ? ` (${history.length})` : ''}
          </Text>
        </TouchableOpacity>
      </View>

      {/* Bookmarks */}
      {tab === 'bookmarks' && (
        !isAuthenticated ? (
          <AuthRequired msg="Đăng nhập để lưu và xem lại các điều luật quan tâm." />
        ) : bookmarkLoading ? (
          <View style={styles.loadingBox}>
            <ActivityIndicator size="large" color={Colors.primary} />
          </View>
        ) : bookmarks.length === 0 ? (
          <View style={styles.emptyBox}>
            <Text style={styles.emptyEmoji}>☆</Text>
            <Text style={styles.emptyTitle}>Chưa có điều luật nào được lưu</Text>
            <Text style={styles.emptyDesc}>Mở bất kỳ điều luật và nhấn "Lưu lại" để thêm vào đây.</Text>
            <TouchableOpacity
              style={styles.ctaBtn}
              // @ts-ignore
              onPress={() => navigation.navigate('Main', { screen: 'LawTab' })}
            >
              <Text style={styles.ctaBtnText}>Duyệt Pháp điển</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <FlatList
            data={bookmarks}
            keyExtractor={(item) => item.mapc}
            renderItem={({ item }) => (
              <DieuCard
                item={item}
                type="bookmark"
                onRemove={handleRemoveBookmark}
                onNavigate={navigateToDieu}
              />
            )}
            contentContainerStyle={styles.listContent}
            showsVerticalScrollIndicator={false}
          />
        )
      )}

      {/* History */}
      {tab === 'history' && (
        !isAuthenticated ? (
          <AuthRequired msg="Đăng nhập để lưu lịch sử xem vào tài khoản." />
        ) : historyLoading ? (
          <View style={styles.loadingBox}>
            <ActivityIndicator size="large" color={Colors.primary} />
          </View>
        ) : history.length === 0 ? (
          <View style={styles.emptyBox}>
            <Text style={styles.emptyEmoji}>🕐</Text>
            <Text style={styles.emptyTitle}>Chưa có lịch sử xem</Text>
            <Text style={styles.emptyDesc}>Các điều luật bạn đã xem sẽ tự động xuất hiện ở đây.</Text>
            <TouchableOpacity
              style={styles.ctaBtn}
              // @ts-ignore
              onPress={() => navigation.navigate('Main', { screen: 'LawTab' })}
            >
              <Text style={styles.ctaBtnText}>Duyệt Pháp điển</Text>
            </TouchableOpacity>
          </View>
        ) : (
          <FlatList
            data={history}
            keyExtractor={(item) => item.mapc}
            renderItem={({ item }) => (
              <DieuCard
                item={item}
                type="history"
                onRemove={handleRemoveHistory}
                onNavigate={navigateToDieu}
              />
            )}
            contentContainerStyle={styles.listContent}
            showsVerticalScrollIndicator={false}
            ListHeaderComponent={
              <View style={styles.toolbar}>
                <Text style={styles.toolbarInfo}>{history.length} điều luật đã xem</Text>
                <TouchableOpacity onPress={handleClearHistory}>
                  <Text style={styles.clearBtn}>Xóa tất cả</Text>
                </TouchableOpacity>
              </View>
            }
          />
        )
      )}
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.background },

  header: {
    backgroundColor: Colors.primary,
    paddingHorizontal: 20,
    paddingVertical: 14,
  },
  headerTitle: { color: '#fff', fontSize: 16, fontWeight: '700' },
  headerSub: { color: 'rgba(255,255,255,0.75)', fontSize: 12, marginTop: 2 },

  tabs: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  tab: {
    flex: 1,
    paddingVertical: 12,
    alignItems: 'center',
    borderBottomWidth: 2,
    borderBottomColor: 'transparent',
  },
  tabActive: { borderBottomColor: Colors.primary },
  tabText: { fontSize: 14, fontWeight: '600', color: Colors.textMuted },
  tabTextActive: { color: Colors.primary },

  loadingBox: { flex: 1, alignItems: 'center', justifyContent: 'center' },

  emptyBox: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32 },
  emptyEmoji: { fontSize: 48, marginBottom: 12 },
  emptyTitle: { fontSize: 16, fontWeight: '700', color: Colors.dark, marginBottom: 8, textAlign: 'center' },
  emptyDesc: { fontSize: 13, color: Colors.textMuted, textAlign: 'center', lineHeight: 18, marginBottom: 20 },
  ctaBtn: {
    backgroundColor: Colors.primary,
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 10,
  },
  ctaBtnText: { color: '#fff', fontWeight: '700', fontSize: 14 },

  listContent: { padding: 14, gap: 10 },

  toolbar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 10,
  },
  toolbarInfo: { fontSize: 13, color: Colors.textMuted },
  clearBtn: { fontSize: 13, color: Colors.error, fontWeight: '600' },

  card: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  breadcrumb: {
    flexDirection: 'row',
    alignItems: 'center',
    flexWrap: 'wrap',
    marginBottom: 8,
    gap: 2,
  },
  bcText: { fontSize: 11, color: Colors.primary, fontWeight: '600', maxWidth: 100 },
  bcSep: { fontSize: 11, color: Colors.textMuted, marginHorizontal: 2 },

  cardMain: { marginBottom: 8 },
  cardTitleWrap: { flex: 1, gap: 3 },
  cardNum: { fontSize: 11, fontWeight: '700', color: Colors.primary },
  cardTitle: { fontSize: 14, fontWeight: '700', color: Colors.dark, lineHeight: 20 },
  cardVb: { fontSize: 11, color: Colors.textMuted, fontStyle: 'italic' },

  cardFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
  },
  cardDate: { fontSize: 11, color: Colors.textMuted },
  removeBtn: {
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 6,
    backgroundColor: '#fff5f5',
    borderWidth: 1,
    borderColor: '#f5c6c2',
  },
  removeBtnText: { fontSize: 12, color: Colors.error, fontWeight: '600' },
})
