import React, { useEffect, useState } from 'react'
import {
  View, Text, StyleSheet, ScrollView, ActivityIndicator,
  TouchableOpacity, Linking,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { RouteProp, useRoute, useNavigation } from '@react-navigation/native'
import { NativeStackNavigationProp } from '@react-navigation/native-stack'
import Markdown from 'react-native-markdown-display'
import {
  getDieuDetail, getBookmarkStatus, toggleBookmark, addHistory,
} from '../services/api'
import { useAuthStore } from '../store/authStore'
import { Colors } from '../theme/colors'
import { DieuDetail, LawStackParamList } from '../types'

type Route = RouteProp<LawStackParamList, 'DieuDetail'>
type NavProp = NativeStackNavigationProp<LawStackParamList, 'DieuDetail'>

export default function DieuDetailScreen() {
  const route = useRoute<Route>()
  const navigation = useNavigation<NavProp>()
  const { isAuthenticated } = useAuthStore()
  const { mapc } = route.params

  const [dieu, setDieu] = useState<DieuDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [bookmarked, setBookmarked] = useState(false)
  const [bookmarkLoading, setBookmarkLoading] = useState(false)

  useEffect(() => {
    setLoading(true)
    getDieuDetail(mapc)
      .then((data) => {
        setDieu(data)
        // Record view history
        if (isAuthenticated) {
          addHistory({
            mapc: data.mapc,
            ten: data.ten,
            chimuc: data.chimuc,
            chude_ten: data.chude_ten,
            demuc_ten: data.demuc_ten,
            chuong_ten: data.chuong_ten,
            vbqppl: data.vbqppl,
          }).catch(() => {})
        }
      })
      .catch(() => setError('Không thể tải nội dung điều luật.'))
      .finally(() => setLoading(false))
  }, [mapc])

  useEffect(() => {
    if (isAuthenticated && mapc) {
      getBookmarkStatus(mapc)
        .then((res) => setBookmarked(res.bookmarked))
        .catch(() => {})
    }
  }, [mapc, isAuthenticated])

  const handleToggleBookmark = async () => {
    if (!isAuthenticated || !dieu) return
    setBookmarkLoading(true)
    try {
      const res = await toggleBookmark({
        mapc: dieu.mapc,
        ten: dieu.ten,
        chimuc: dieu.chimuc,
        chude_ten: dieu.chude_ten,
        demuc_ten: dieu.demuc_ten,
        chuong_ten: dieu.chuong_ten,
        vbqppl: dieu.vbqppl,
      })
      setBookmarked(res.bookmarked)
    } catch {}
    finally { setBookmarkLoading(false) }
  }

  if (loading) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.center}>
          <ActivityIndicator size="large" color={Colors.primary} />
          <Text style={styles.loadingText}>Đang tải...</Text>
        </View>
      </SafeAreaView>
    )
  }

  if (error || !dieu) {
    return (
      <SafeAreaView style={styles.safe}>
        <View style={styles.center}>
          <Text style={styles.errorEmoji}>😕</Text>
          <Text style={styles.errorText}>{error || 'Không tìm thấy điều luật.'}</Text>
        </View>
      </SafeAreaView>
    )
  }

  // Strip HTML for display
  const stripHtml = (html: string) =>
    html.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      {/* Bookmark action bar */}
      {isAuthenticated && (
        <View style={styles.actionBar}>
          <TouchableOpacity
            style={[styles.bookmarkBtn, bookmarked && styles.bookmarkBtnActive]}
            onPress={handleToggleBookmark}
            disabled={bookmarkLoading}
          >
            {bookmarkLoading ? (
              <ActivityIndicator size="small" color={bookmarked ? '#fff' : Colors.primary} />
            ) : (
              <>
                <Text style={[styles.bookmarkIcon, bookmarked && styles.bookmarkIconActive]}>
                  {bookmarked ? '★' : '☆'}
                </Text>
                <Text style={[styles.bookmarkText, bookmarked && styles.bookmarkTextActive]}>
                  {bookmarked ? 'Đã lưu' : 'Lưu lại'}
                </Text>
              </>
            )}
          </TouchableOpacity>
        </View>
      )}

      <ScrollView showsVerticalScrollIndicator={false}>
        {/* Metadata card */}
        <View style={styles.metaCard}>
          {dieu.chude_ten && (
            <View style={styles.tagRow}>
              <View style={styles.tag}>
                <Text style={styles.tagText}>{dieu.chude_ten}</Text>
              </View>
              {dieu.demuc_ten && (
                <View style={[styles.tag, { backgroundColor: '#eef6ff' }]}>
                  <Text style={[styles.tagText, { color: '#2980b9' }]}>{dieu.demuc_ten}</Text>
                </View>
              )}
            </View>
          )}

          <Text style={styles.mapc}>{dieu.chimuc || dieu.mapc}</Text>
          <Text style={styles.title}>{dieu.ten}</Text>

          {dieu.chuong_ten && (
            <Text style={styles.chuongTen}>📑 {dieu.chuong_ten}</Text>
          )}

          {dieu.vbqppl && (
            <TouchableOpacity
              style={styles.vbRow}
              onPress={() => dieu.vbqppl_link && Linking.openURL(dieu.vbqppl_link)}
              activeOpacity={dieu.vbqppl_link ? 0.7 : 1}
            >
              <Text style={styles.vbIcon}>📄</Text>
              <Text style={[styles.vbText, !!dieu.vbqppl_link && styles.vbLink]} numberOfLines={2}>
                {dieu.vbqppl}
              </Text>
              {dieu.vbqppl_link && <Text style={styles.vbArrow}>↗</Text>}
            </TouchableOpacity>
          )}
        </View>

        {/* Content */}
        <View style={styles.contentCard}>
          <Text style={styles.sectionLabel}>Nội dung</Text>
          {dieu.noidung ? (
            <Markdown style={markdownStyles}>{stripHtml(dieu.noidung)}</Markdown>
          ) : (
            <Text style={styles.emptyContent}>Không có nội dung.</Text>
          )}
        </View>

        {/* Tables */}
        {dieu.tables && dieu.tables.length > 0 && (
          <View style={styles.contentCard}>
            <Text style={styles.sectionLabel}>Bảng dữ liệu ({dieu.tables.length})</Text>
            {dieu.tables.map((table, idx) => (
              <View key={table.id} style={styles.tableBox}>
                <Text style={styles.tableLabel}>Bảng {idx + 1}</Text>
                <Text style={styles.tableContent}>{stripHtml(table.html)}</Text>
              </View>
            ))}
          </View>
        )}

        {/* Related articles */}
        {dieu.related && dieu.related.length > 0 && (
          <View style={styles.contentCard}>
            <Text style={styles.sectionLabel}>Điều liên quan ({dieu.related.length})</Text>
            {dieu.related.map((rel) => (
              <TouchableOpacity
                key={rel.mapc}
                style={styles.relatedItem}
                onPress={() => navigation.push('DieuDetail', { mapc: rel.mapc })}
                activeOpacity={0.7}
              >
                <View style={styles.relatedLeft}>
                  <Text style={styles.relatedMacp}>{rel.chimuc || rel.mapc}</Text>
                  <Text style={styles.relatedTitle} numberOfLines={2}>{rel.ten}</Text>
                </View>
                <Text style={styles.relatedArrow}>›</Text>
              </TouchableOpacity>
            ))}
          </View>
        )}

        <View style={{ height: 32 }} />
      </ScrollView>
    </SafeAreaView>
  )
}

const markdownStyles = {
  body: { color: Colors.text, fontSize: 14, lineHeight: 22 },
  paragraph: { marginBottom: 10, fontSize: 14, color: Colors.text, lineHeight: 22 },
  strong: { fontWeight: '700' as const, color: Colors.dark },
  heading1: { fontSize: 16, fontWeight: '800' as const, color: Colors.dark, marginBottom: 8 },
  heading2: { fontSize: 15, fontWeight: '700' as const, color: Colors.dark, marginBottom: 6 },
  bullet_list: { marginLeft: 12 },
  ordered_list: { marginLeft: 12 },
  list_item: { marginBottom: 6, fontSize: 14, color: Colors.text },
  blockquote: { borderLeftWidth: 3, borderLeftColor: Colors.border, paddingLeft: 12 },
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.background },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32 },
  loadingText: { marginTop: 12, color: Colors.textMuted },
  errorEmoji: { fontSize: 48, marginBottom: 12 },
  errorText: { fontSize: 14, color: Colors.textMuted, textAlign: 'center' },

  actionBar: {
    backgroundColor: '#fff',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
    flexDirection: 'row',
    justifyContent: 'flex-end',
  },
  bookmarkBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 16,
    paddingVertical: 7,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: Colors.primary,
    backgroundColor: '#fff',
  },
  bookmarkBtnActive: {
    backgroundColor: Colors.primary,
  },
  bookmarkIcon: { fontSize: 16, color: Colors.primary },
  bookmarkIconActive: { color: '#fff' },
  bookmarkText: { fontSize: 13, fontWeight: '600', color: Colors.primary },
  bookmarkTextActive: { color: '#fff' },

  metaCard: {
    backgroundColor: Colors.cardBg,
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  tagRow: { flexDirection: 'row', gap: 6, marginBottom: 10, flexWrap: 'wrap' },
  tag: {
    backgroundColor: Colors.primaryLight,
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  tagText: { fontSize: 11, fontWeight: '600', color: Colors.primary },
  mapc: { fontSize: 12, fontWeight: '700', color: Colors.primary, marginBottom: 6 },
  title: { fontSize: 18, fontWeight: '800', color: Colors.dark, lineHeight: 24, marginBottom: 8 },
  chuongTen: { fontSize: 12, color: Colors.textSecondary, marginBottom: 10 },

  vbRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: Colors.background,
    borderRadius: 8,
    padding: 10,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  vbIcon: { fontSize: 14, flexShrink: 0 },
  vbText: { flex: 1, fontSize: 12, color: Colors.textSecondary },
  vbLink: { color: Colors.primary, textDecorationLine: 'underline' },
  vbArrow: { fontSize: 14, color: Colors.primary, flexShrink: 0 },

  contentCard: {
    backgroundColor: Colors.cardBg,
    margin: 12,
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  sectionLabel: {
    fontSize: 12,
    fontWeight: '700',
    color: Colors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginBottom: 12,
  },
  emptyContent: { fontSize: 13, color: Colors.textMuted, fontStyle: 'italic' },

  tableBox: {
    backgroundColor: Colors.background,
    borderRadius: 8,
    padding: 10,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  tableLabel: { fontSize: 11, fontWeight: '700', color: Colors.textMuted, marginBottom: 6 },
  tableContent: { fontSize: 13, color: Colors.text, lineHeight: 18 },

  relatedItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 10,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: Colors.border,
    marginBottom: 8,
    gap: 8,
    backgroundColor: Colors.background,
  },
  relatedLeft: { flex: 1 },
  relatedMacp: { fontSize: 11, fontWeight: '700', color: Colors.primary, marginBottom: 2 },
  relatedTitle: { fontSize: 12, color: Colors.dark, lineHeight: 16 },
  relatedArrow: { fontSize: 20, color: Colors.textMuted },
})
