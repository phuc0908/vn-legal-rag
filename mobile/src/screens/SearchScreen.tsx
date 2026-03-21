import React, { useState, useEffect, useCallback } from 'react'
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  FlatList, ActivityIndicator, Linking,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { useRoute, RouteProp } from '@react-navigation/native'
import { searchLaw } from '../services/api'
import { Colors } from '../theme/colors'
import { SearchResult, MainTabParamList } from '../types'

type Route = RouteProp<MainTabParamList, 'SearchTab'>

export default function SearchScreen() {
  const route = useRoute<Route>()
  const initialQ = route.params?.q || ''

  const [query, setQuery] = useState(initialQ)
  const [results, setResults] = useState<SearchResult[]>([])
  const [loading, setLoading] = useState(false)
  const [searched, setSearched] = useState(false)
  const [total, setTotal] = useState(0)

  const doSearch = useCallback(async (q: string) => {
    if (!q.trim()) return
    setLoading(true)
    setSearched(true)
    try {
      const data = await searchLaw(q.trim())
      setResults(data.results || [])
      setTotal(data.total || 0)
    } catch {
      setResults([])
    } finally {
      setLoading(false)
    }
  }, [])

  // Auto-search nếu có query từ HomeScreen
  useEffect(() => {
    if (initialQ) {
      setQuery(initialQ)
      doSearch(initialQ)
    }
  }, [initialQ])

  const renderItem = ({ item }: { item: SearchResult }) => (
    <View style={styles.resultCard}>
      <View style={styles.resultHeader}>
        <View style={styles.badge}>
          <Text style={styles.badgeText}>{item.chude_ten}</Text>
        </View>
        <Text style={styles.resultMacp}>{item.mapc}</Text>
      </View>
      <Text style={styles.resultTitle} numberOfLines={2}>{item.ten}</Text>
      {item.noidung_preview ? (
        <Text style={styles.resultPreview} numberOfLines={3}>
          {item.noidung_preview}
        </Text>
      ) : null}
      <Text style={styles.resultDemuc}>{item.demuc_ten}</Text>
    </View>
  )

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>🔍 Tra cứu Pháp luật</Text>
      </View>

      {/* Search Bar */}
      <View style={styles.searchArea}>
        <View style={styles.searchRow}>
          <TextInput
            style={styles.searchInput}
            value={query}
            onChangeText={setQuery}
            placeholder="Tìm điều luật, quy định, nội dung..."
            placeholderTextColor={Colors.textPlaceholder}
            returnKeyType="search"
            onSubmitEditing={() => doSearch(query)}
          />
          <TouchableOpacity
            style={[styles.searchBtn, !query.trim() && styles.searchBtnDisabled]}
            onPress={() => doSearch(query)}
            disabled={!query.trim()}
          >
            <Text style={styles.searchBtnText}>Tìm</Text>
          </TouchableOpacity>
        </View>
        {searched && !loading && (
          <Text style={styles.resultCount}>
            {total > 0 ? `Tìm thấy ${total.toLocaleString()} kết quả` : 'Không tìm thấy kết quả'}
          </Text>
        )}
      </View>

      {/* Results */}
      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color={Colors.primary} />
          <Text style={styles.loadingText}>Đang tìm kiếm...</Text>
        </View>
      ) : !searched ? (
        <View style={styles.center}>
          <Text style={styles.emptyEmoji}>🔍</Text>
          <Text style={styles.emptyTitle}>Nhập từ khóa để tra cứu</Text>
          <Text style={styles.emptyDesc}>Tìm theo tên điều, nội dung điều luật, số hiệu văn bản...</Text>
        </View>
      ) : results.length === 0 ? (
        <View style={styles.center}>
          <Text style={styles.emptyEmoji}>😕</Text>
          <Text style={styles.emptyTitle}>Không tìm thấy kết quả</Text>
          <Text style={styles.emptyDesc}>Thử tìm với từ khóa khác hoặc câu hỏi ngắn hơn</Text>
        </View>
      ) : (
        <FlatList
          data={results}
          keyExtractor={(item) => item.mapc}
          renderItem={renderItem}
          contentContainerStyle={{ padding: 16, gap: 10 }}
          showsVerticalScrollIndicator={false}
        />
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

  searchArea: {
    backgroundColor: '#fff',
    padding: 14,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  searchRow: { flexDirection: 'row', gap: 8, alignItems: 'center' },
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
  resultCount: { fontSize: 12, color: Colors.textMuted, marginTop: 6 },

  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: 32 },
  loadingText: { marginTop: 12, color: Colors.textMuted, fontSize: 14 },
  emptyEmoji: { fontSize: 48, marginBottom: 12 },
  emptyTitle: { fontSize: 16, fontWeight: '700', color: Colors.dark, marginBottom: 8 },
  emptyDesc: { fontSize: 13, color: Colors.textMuted, textAlign: 'center', lineHeight: 18 },

  resultCard: {
    backgroundColor: Colors.cardBg,
    borderRadius: 12,
    padding: 14,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  resultHeader: { flexDirection: 'row', alignItems: 'center', gap: 8, marginBottom: 6 },
  badge: {
    backgroundColor: Colors.primaryLight,
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  badgeText: { color: Colors.primary, fontSize: 11, fontWeight: '600' },
  resultMacp: { fontSize: 11, color: Colors.textMuted },
  resultTitle: { fontSize: 14, fontWeight: '700', color: Colors.dark, marginBottom: 6, lineHeight: 20 },
  resultPreview: { fontSize: 12, color: Colors.textSecondary, lineHeight: 17, marginBottom: 6 },
  resultDemuc: { fontSize: 11, color: Colors.textMuted, fontStyle: 'italic' },
})
