import React, { useState, useEffect, useCallback } from 'react'
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  ScrollView, ActivityIndicator,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { useRoute, RouteProp, useNavigation } from '@react-navigation/native'
import { BottomTabNavigationProp } from '@react-navigation/bottom-tabs'
import Markdown from 'react-native-markdown-display'
import { sendMessage } from '../services/api'
import { Colors } from '../theme/colors'
import { MainTabParamList } from '../types'

type Route = RouteProp<MainTabParamList, 'SearchTab'>
type NavProp = BottomTabNavigationProp<MainTabParamList>

interface SearchResult {
  answer: string
  sources?: { title?: string; source?: string; score?: number }[]
  processing_time?: number
  model_used?: string
}

export default function SearchScreen() {
  const route = useRoute<Route>()
  const navigation = useNavigation<NavProp>()
  const initialQ = route.params?.q || ''

  const [query, setQuery] = useState(initialQ)
  const [inputValue, setInputValue] = useState(initialQ)
  const [result, setResult] = useState<SearchResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [searched, setSearched] = useState(false)

  const doSearch = useCallback(async (q: string) => {
    if (!q.trim()) return
    setLoading(true)
    setError('')
    setResult(null)
    setSearched(true)
    try {
      const data = await sendMessage(q.trim(), null)
      setResult(data)
    } catch {
      setError('Không thể kết nối đến máy chủ. Vui lòng thử lại.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (initialQ) {
      setInputValue(initialQ)
      setQuery(initialQ)
      doSearch(initialQ)
    }
  }, [initialQ])

  const handleSubmit = () => {
    const q = inputValue.trim()
    if (!q) return
    setQuery(q)
    doSearch(q)
  }

  const handleAskAI = () => {
    // @ts-ignore
    navigation.navigate('ChatTab', { q: query })
  }

  const RELATED = [
    'Tội trộm cắp tài sản',
    'Hợp đồng lao động',
    'Quyền sử dụng đất',
    'Ly hôn và tài sản',
    'Thành lập doanh nghiệp',
    'Vi phạm giao thông',
  ]

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>🔍 Tra cứu Pháp luật</Text>
      </View>

      {/* Search Bar */}
      <View style={styles.searchArea}>
        <View style={styles.searchRow}>
          <Text style={styles.searchIcon}>🔍</Text>
          <TextInput
            style={styles.searchInput}
            value={inputValue}
            onChangeText={setInputValue}
            placeholder="Nhập nội dung pháp lý cần tra cứu..."
            placeholderTextColor={Colors.textPlaceholder}
            returnKeyType="search"
            onSubmitEditing={handleSubmit}
          />
          <TouchableOpacity
            style={[styles.searchBtn, !inputValue.trim() && styles.searchBtnDisabled]}
            onPress={handleSubmit}
            disabled={!inputValue.trim()}
          >
            <Text style={styles.searchBtnText}>Tìm</Text>
          </TouchableOpacity>
        </View>
      </View>

      <ScrollView showsVerticalScrollIndicator={false} keyboardShouldPersistTaps="handled">
        {/* Empty state */}
        {!searched && !loading && (
          <View style={styles.center}>
            <Text style={styles.emptyEmoji}>⚖️</Text>
            <Text style={styles.emptyTitle}>Tra cứu văn bản pháp luật</Text>
            <Text style={styles.emptyDesc}>
              Nhập từ khóa, câu hỏi hoặc tên điều luật vào ô tìm kiếm phía trên để bắt đầu.
            </Text>

            {/* Related suggestions */}
            <View style={styles.suggestBox}>
              <Text style={styles.suggestTitle}>Tìm kiếm phổ biến</Text>
              {RELATED.map((s) => (
                <TouchableOpacity
                  key={s}
                  style={styles.suggestItem}
                  onPress={() => { setInputValue(s); setQuery(s); doSearch(s) }}
                >
                  <Text style={styles.suggestIcon}>🔎</Text>
                  <Text style={styles.suggestText}>{s}</Text>
                  <Text style={styles.suggestArrow}>›</Text>
                </TouchableOpacity>
              ))}
            </View>
          </View>
        )}

        {/* Loading */}
        {loading && (
          <View style={styles.center}>
            <ActivityIndicator size="large" color={Colors.primary} />
            <Text style={styles.loadingText}>Đang tìm kiếm trong cơ sở dữ liệu pháp luật...</Text>
          </View>
        )}

        {/* Error */}
        {error && !loading && (
          <View style={styles.center}>
            <Text style={styles.emptyEmoji}>⚠️</Text>
            <Text style={styles.emptyTitle}>Không thể kết nối</Text>
            <Text style={styles.emptyDesc}>{error}</Text>
            <TouchableOpacity style={styles.retryBtn} onPress={() => doSearch(query)}>
              <Text style={styles.retryBtnText}>Thử lại</Text>
            </TouchableOpacity>
          </View>
        )}

        {/* Result */}
        {result && !loading && (
          <View style={styles.resultWrap}>
            {/* Result header */}
            <View style={styles.resultHeader}>
              <Text style={styles.resultTitle}>Kết quả tra cứu</Text>
              <Text style={styles.resultQuery}>"{query}"</Text>
              {result.processing_time !== undefined && (
                <Text style={styles.resultMeta}>
                  {(result.processing_time * 1000).toFixed(0)}ms · {result.model_used || 'AI'}
                </Text>
              )}
            </View>

            {/* Answer card */}
            <View style={styles.answerCard}>
              <View style={styles.answerLabel}>
                <Text style={styles.answerLabelText}>⚖️  Thông tin pháp lý</Text>
              </View>
              <Markdown style={mdStyles}>{result.answer}</Markdown>

              {/* Sources */}
              {result.sources && result.sources.length > 0 && (
                <View style={styles.sourcesBox}>
                  <Text style={styles.sourcesTitle}>Nguồn văn bản tham khảo</Text>
                  {result.sources.map((src, idx) => (
                    <View key={idx} style={styles.sourceItem}>
                      <View style={styles.sourceNum}>
                        <Text style={styles.sourceNumText}>{idx + 1}</Text>
                      </View>
                      <View style={styles.sourceInfo}>
                        <Text style={styles.sourceTitle} numberOfLines={2}>
                          {src.title || src.source || `Văn bản ${idx + 1}`}
                        </Text>
                        {src.score !== undefined && (
                          <Text style={styles.sourceScore}>
                            Độ liên quan: {Math.round(src.score * 100)}%
                          </Text>
                        )}
                      </View>
                    </View>
                  ))}
                </View>
              )}
            </View>

            {/* Actions */}
            <View style={styles.actions}>
              <TouchableOpacity style={[styles.actionBtn, styles.actionBtnPrimary]} onPress={handleAskAI}>
                <Text style={styles.actionBtnPrimaryText}>🤖 Hỏi thêm với AI</Text>
              </TouchableOpacity>
              <TouchableOpacity style={styles.actionBtn} onPress={() => doSearch(query)}>
                <Text style={styles.actionBtnText}>🔄 Tìm lại</Text>
              </TouchableOpacity>
            </View>

            {/* Related */}
            <View style={styles.relatedBox}>
              <Text style={styles.suggestTitle}>Tìm kiếm liên quan</Text>
              {RELATED.map((s) => (
                <TouchableOpacity
                  key={s}
                  style={styles.suggestItem}
                  onPress={() => { setInputValue(s); setQuery(s); doSearch(s) }}
                >
                  <Text style={styles.suggestIcon}>🔎</Text>
                  <Text style={styles.suggestText}>{s}</Text>
                  <Text style={styles.suggestArrow}>›</Text>
                </TouchableOpacity>
              ))}
            </View>

            {/* AI CTA */}
            <View style={styles.aiCtaBox}>
              <Text style={styles.aiCtaEmoji}>🤖</Text>
              <Text style={styles.aiCtaTitle}>Cần giải thích chi tiết?</Text>
              <Text style={styles.aiCtaDesc}>
                Trợ lý AI có thể phân tích và giải thích điều luật theo ngôn ngữ dễ hiểu
              </Text>
              <TouchableOpacity
                style={[styles.actionBtn, styles.actionBtnPrimary]}
                onPress={() => navigation.navigate('ChatTab')}
              >
                <Text style={styles.actionBtnPrimaryText}>Tư vấn AI ngay</Text>
              </TouchableOpacity>
            </View>
          </View>
        )}

        <View style={{ height: 24 }} />
      </ScrollView>
    </SafeAreaView>
  )
}

const mdStyles = {
  body: { color: Colors.text, fontSize: 14, lineHeight: 22 },
  paragraph: { marginBottom: 10, fontSize: 14, color: Colors.text, lineHeight: 22 },
  strong: { fontWeight: '700' as const, color: Colors.dark },
  heading1: { fontSize: 16, fontWeight: '800' as const, color: Colors.dark, marginBottom: 8 },
  heading2: { fontSize: 15, fontWeight: '700' as const, color: Colors.dark, marginBottom: 6 },
  bullet_list: { marginLeft: 8 },
  ordered_list: { marginLeft: 8 },
  list_item: { marginBottom: 4, fontSize: 14, color: Colors.text },
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.background },

  header: {
    backgroundColor: Colors.primary,
    paddingHorizontal: 20,
    paddingVertical: 14,
  },
  headerTitle: { color: '#fff', fontSize: 16, fontWeight: '700' },

  searchArea: {
    backgroundColor: '#fff',
    padding: 12,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  searchRow: { flexDirection: 'row', gap: 8, alignItems: 'center' },
  searchIcon: { fontSize: 16 },
  searchInput: {
    flex: 1,
    borderWidth: 1,
    borderColor: Colors.borderDark,
    borderRadius: 8,
    paddingHorizontal: 12,
    paddingVertical: 9,
    fontSize: 14,
    color: Colors.text,
    backgroundColor: Colors.inputBg,
  },
  searchBtn: {
    backgroundColor: Colors.primary,
    paddingHorizontal: 18,
    paddingVertical: 10,
    borderRadius: 8,
  },
  searchBtnDisabled: { opacity: 0.4 },
  searchBtnText: { color: '#fff', fontWeight: '700', fontSize: 14 },

  center: { padding: 32, alignItems: 'center' },
  emptyEmoji: { fontSize: 48, marginBottom: 12 },
  emptyTitle: { fontSize: 16, fontWeight: '700', color: Colors.dark, marginBottom: 8, textAlign: 'center' },
  emptyDesc: { fontSize: 13, color: Colors.textMuted, textAlign: 'center', lineHeight: 18, marginBottom: 20 },
  loadingText: { marginTop: 12, color: Colors.textMuted, fontSize: 14, textAlign: 'center' },

  retryBtn: {
    backgroundColor: Colors.primary,
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 8,
  },
  retryBtnText: { color: '#fff', fontWeight: '700', fontSize: 14 },

  resultWrap: { padding: 16, gap: 12 },

  resultHeader: { gap: 4 },
  resultTitle: { fontSize: 18, fontWeight: '800', color: Colors.dark },
  resultQuery: { fontSize: 14, color: Colors.textSecondary, fontStyle: 'italic' },
  resultMeta: { fontSize: 11, color: Colors.textMuted },

  answerCard: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 16,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  answerLabel: {
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
    paddingBottom: 10,
    marginBottom: 12,
  },
  answerLabelText: { fontSize: 13, fontWeight: '700', color: Colors.primary },

  sourcesBox: {
    marginTop: 12,
    paddingTop: 12,
    borderTopWidth: 1,
    borderTopColor: Colors.border,
  },
  sourcesTitle: { fontSize: 13, fontWeight: '700', color: Colors.dark, marginBottom: 10 },
  sourceItem: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
    marginBottom: 8,
  },
  sourceNum: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: Colors.primaryLight,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
    marginTop: 1,
  },
  sourceNumText: { fontSize: 11, fontWeight: '700', color: Colors.primary },
  sourceInfo: { flex: 1 },
  sourceTitle: { fontSize: 13, color: Colors.dark, lineHeight: 18 },
  sourceScore: { fontSize: 11, color: Colors.textMuted, marginTop: 2 },

  actions: { flexDirection: 'row', gap: 10 },
  actionBtn: {
    flex: 1,
    borderWidth: 1,
    borderColor: Colors.border,
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: 'center',
  },
  actionBtnPrimary: {
    backgroundColor: Colors.primary,
    borderColor: Colors.primary,
  },
  actionBtnPrimaryText: { color: '#fff', fontWeight: '700', fontSize: 14 },
  actionBtnText: { color: Colors.dark, fontWeight: '600', fontSize: 14 },

  suggestBox: {
    width: '100%',
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: Colors.border,
    marginTop: 8,
  },
  relatedBox: {
    backgroundColor: '#fff',
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  suggestTitle: { fontSize: 14, fontWeight: '700', color: Colors.dark, marginBottom: 10 },
  suggestItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 9,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  suggestIcon: { fontSize: 14 },
  suggestText: { flex: 1, fontSize: 13, color: Colors.text },
  suggestArrow: { fontSize: 16, color: Colors.textMuted },

  aiCtaBox: {
    backgroundColor: Colors.dark,
    borderRadius: 12,
    padding: 16,
    alignItems: 'center',
    gap: 8,
  },
  aiCtaEmoji: { fontSize: 32 },
  aiCtaTitle: { fontSize: 16, fontWeight: '800', color: '#fff' },
  aiCtaDesc: { fontSize: 13, color: 'rgba(255,255,255,0.75)', textAlign: 'center', lineHeight: 18, marginBottom: 4 },
})
