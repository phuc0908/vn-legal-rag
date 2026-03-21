import React, { useState, useEffect } from 'react'
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  ScrollView, FlatList, ActivityIndicator,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { useNavigation } from '@react-navigation/native'
import { BottomTabNavigationProp } from '@react-navigation/bottom-tabs'
import { getLawStats } from '../services/api'
import { Colors } from '../theme/colors'
import { LawStats, MainTabParamList } from '../types'

type NavProp = BottomTabNavigationProp<MainTabParamList>

const LAW_CATEGORIES = [
  { icon: '⚖️', label: 'Bộ luật Hình sự', query: 'bộ luật hình sự', color: '#e74c3c' },
  { icon: '📜', label: 'Bộ luật Dân sự', query: 'bộ luật dân sự', color: '#2980b9' },
  { icon: '👷', label: 'Luật Lao động', query: 'bộ luật lao động', color: '#27ae60' },
  { icon: '🏢', label: 'Luật Doanh nghiệp', query: 'luật doanh nghiệp', color: '#8e44ad' },
  { icon: '🏠', label: 'Luật Đất đai', query: 'luật đất đai', color: '#d35400' },
  { icon: '💍', label: 'Hôn nhân & Gia đình', query: 'luật hôn nhân gia đình', color: '#c0392b' },
  { icon: '🚗', label: 'Luật Giao thông', query: 'luật giao thông đường bộ', color: '#16a085' },
  { icon: '🏛️', label: 'Luật Hành chính', query: 'luật hành chính', color: '#2c3e50' },
]

const COMMON_QUESTIONS = [
  'Tội trộm cắp bị phạt bao nhiêu năm?',
  'Quy định về hợp đồng lao động',
  'Thủ tục đăng ký kết hôn',
  'Mức phạt vi phạm giao thông',
  'Quyền và nghĩa vụ của người thuê nhà',
  'Điều kiện thành lập công ty',
]

export default function HomeScreen() {
  const navigation = useNavigation<NavProp>()
  const [searchQuery, setSearchQuery] = useState('')
  const [lawStats, setLawStats] = useState<LawStats | null>(null)

  useEffect(() => {
    getLawStats().then(setLawStats).catch(() => {})
  }, [])

  const goSearch = (q: string) => {
    // @ts-ignore – navigate cross-tab with params
    navigation.navigate('SearchTab', { q })
  }

  const goChat = () => navigation.navigate('ChatTab')

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      {/* Header */}
      <View style={styles.header}>
        <Text style={styles.headerEmoji}>⚖️</Text>
        <View>
          <Text style={styles.headerTitle}>Trợ lý Pháp lý VN</Text>
          <Text style={styles.headerSub}>Hệ thống pháp luật Việt Nam</Text>
        </View>
      </View>

      <ScrollView showsVerticalScrollIndicator={false}>
        {/* Hero search */}
        <View style={styles.hero}>
          <Text style={styles.heroTitle}>Tra cứu pháp luật</Text>
          <Text style={styles.heroAccent}>nhanh chóng & chính xác</Text>
          <Text style={styles.heroSub}>
            Tìm kiếm điều luật, quy định từ hàng nghìn văn bản pháp lý Việt Nam
          </Text>

          <View style={styles.searchRow}>
            <Text style={styles.searchIcon}>🔍</Text>
            <TextInput
              style={styles.searchInput}
              placeholder="Nhập điều luật, nội dung pháp lý..."
              placeholderTextColor={Colors.textPlaceholder}
              value={searchQuery}
              onChangeText={setSearchQuery}
              onSubmitEditing={() => searchQuery.trim() && goSearch(searchQuery.trim())}
              returnKeyType="search"
            />
            <TouchableOpacity
              style={[styles.searchBtn, !searchQuery.trim() && styles.searchBtnDisabled]}
              onPress={() => searchQuery.trim() && goSearch(searchQuery.trim())}
              disabled={!searchQuery.trim()}
            >
              <Text style={styles.searchBtnText}>Tìm</Text>
            </TouchableOpacity>
          </View>

          {/* Quick tags */}
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.quickRow}>
            {COMMON_QUESTIONS.slice(0, 4).map((q) => (
              <TouchableOpacity key={q} style={styles.quickTag} onPress={() => goSearch(q)}>
                <Text style={styles.quickTagText}>{q}</Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>

        {/* Stats bar */}
        {lawStats && (
          <View style={styles.statsBar}>
            <View style={styles.statItem}>
              <Text style={styles.statNum}>{lawStats.chude}</Text>
              <Text style={styles.statLabel}>Chủ đề</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.statItem}>
              <Text style={styles.statNum}>{lawStats.demuc}</Text>
              <Text style={styles.statLabel}>Đề mục</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.statItem}>
              <Text style={styles.statNum}>{lawStats.dieu.toLocaleString()}</Text>
              <Text style={styles.statLabel}>Điều luật</Text>
            </View>
            <View style={styles.statDivider} />
            <View style={styles.statItem}>
              <Text style={styles.statNum}>24/7</Text>
              <Text style={styles.statLabel}>Miễn phí</Text>
            </View>
          </View>
        )}

        {/* AI Chat CTA */}
        <TouchableOpacity style={styles.ctaCard} onPress={goChat} activeOpacity={0.85}>
          <View style={styles.ctaBadge}>
            <Text style={styles.ctaBadgeText}>Nổi bật</Text>
          </View>
          <Text style={styles.ctaEmoji}>🤖</Text>
          <Text style={styles.ctaTitle}>Tư vấn AI</Text>
          <Text style={styles.ctaDesc}>
            Đặt câu hỏi bằng tiếng Việt, nhận giải thích chi tiết có trích dẫn điều luật cụ thể.
          </Text>
          <View style={styles.ctaBtn}>
            <Text style={styles.ctaBtnText}>Tư vấn ngay →</Text>
          </View>
        </TouchableOpacity>

        {/* Law Categories */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Lĩnh vực pháp luật</Text>
          <Text style={styles.sectionSub}>Chọn lĩnh vực để tra cứu văn bản liên quan</Text>
          <View style={styles.categoriesGrid}>
            {LAW_CATEGORIES.map((cat) => (
              <TouchableOpacity
                key={cat.label}
                style={styles.categoryCard}
                onPress={() => goSearch(cat.query)}
                activeOpacity={0.75}
              >
                <View style={[styles.catIconWrap, { backgroundColor: cat.color + '18' }]}>
                  <Text style={styles.catIconText}>{cat.icon}</Text>
                </View>
                <Text style={styles.catLabel} numberOfLines={2}>{cat.label}</Text>
              </TouchableOpacity>
            ))}
          </View>
        </View>

        {/* Common Questions */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Câu hỏi thường gặp</Text>
          <Text style={styles.sectionSub}>Nhấn để tra cứu ngay</Text>
          {COMMON_QUESTIONS.map((q) => (
            <TouchableOpacity key={q} style={styles.questionCard} onPress={() => goSearch(q)}>
              <Text style={styles.questionIcon}>❓</Text>
              <Text style={styles.questionText}>{q}</Text>
              <Text style={styles.questionArrow}>→</Text>
            </TouchableOpacity>
          ))}
        </View>

        <View style={{ height: 24 }} />
      </ScrollView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.background },

  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingHorizontal: 20,
    paddingVertical: 12,
    backgroundColor: Colors.primary,
  },
  headerEmoji: { fontSize: 26 },
  headerTitle: { fontSize: 16, fontWeight: '800', color: '#fff' },
  headerSub: { fontSize: 11, color: 'rgba(255,255,255,0.75)' },

  hero: {
    backgroundColor: Colors.primary,
    paddingHorizontal: 20,
    paddingBottom: 28,
    paddingTop: 4,
  },
  heroTitle: { fontSize: 26, fontWeight: '800', color: '#fff', lineHeight: 34 },
  heroAccent: { fontSize: 26, fontWeight: '800', color: '#ffcdd2', lineHeight: 34 },
  heroSub: { fontSize: 13, color: 'rgba(255,255,255,0.8)', marginTop: 8, marginBottom: 16, lineHeight: 18 },

  searchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 10,
    paddingHorizontal: 12,
    gap: 8,
  },
  searchIcon: { fontSize: 16 },
  searchInput: { flex: 1, fontSize: 14, color: Colors.text, paddingVertical: 12 },
  searchBtn: {
    backgroundColor: Colors.primaryDark,
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 8,
  },
  searchBtnDisabled: { opacity: 0.4 },
  searchBtnText: { color: '#fff', fontWeight: '700', fontSize: 13 },

  quickRow: { marginTop: 12 },
  quickTag: {
    backgroundColor: 'rgba(255,255,255,0.2)',
    borderRadius: 20,
    paddingHorizontal: 12,
    paddingVertical: 6,
    marginRight: 8,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.3)',
  },
  quickTagText: { color: '#fff', fontSize: 12 },

  statsBar: {
    flexDirection: 'row',
    backgroundColor: '#fff',
    paddingVertical: 14,
    paddingHorizontal: 8,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  statItem: { flex: 1, alignItems: 'center' },
  statNum: { fontSize: 18, fontWeight: '800', color: Colors.primary },
  statLabel: { fontSize: 11, color: Colors.textMuted, marginTop: 2 },
  statDivider: { width: 1, backgroundColor: Colors.border },

  ctaCard: {
    margin: 16,
    backgroundColor: Colors.dark,
    borderRadius: 16,
    padding: 20,
    position: 'relative',
    overflow: 'hidden',
  },
  ctaBadge: {
    position: 'absolute',
    top: 16,
    right: 16,
    backgroundColor: Colors.primary,
    borderRadius: 12,
    paddingHorizontal: 10,
    paddingVertical: 3,
  },
  ctaBadgeText: { color: '#fff', fontSize: 11, fontWeight: '700' },
  ctaEmoji: { fontSize: 36, marginBottom: 8 },
  ctaTitle: { fontSize: 22, fontWeight: '800', color: '#fff', marginBottom: 8 },
  ctaDesc: { fontSize: 13, color: 'rgba(255,255,255,0.75)', lineHeight: 18, marginBottom: 16 },
  ctaBtn: {
    backgroundColor: Colors.primary,
    borderRadius: 10,
    paddingVertical: 12,
    alignItems: 'center',
  },
  ctaBtnText: { color: '#fff', fontWeight: '700', fontSize: 14 },

  section: { paddingHorizontal: 16, paddingTop: 24 },
  sectionTitle: { fontSize: 18, fontWeight: '800', color: Colors.dark, marginBottom: 4 },
  sectionSub: { fontSize: 13, color: Colors.textMuted, marginBottom: 16 },

  categoriesGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: 10 },
  categoryCard: {
    width: '47%',
    backgroundColor: Colors.cardBg,
    borderRadius: 12,
    padding: 14,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  catIconWrap: { width: 38, height: 38, borderRadius: 8, alignItems: 'center', justifyContent: 'center' },
  catIconText: { fontSize: 20 },
  catLabel: { flex: 1, fontSize: 12, fontWeight: '600', color: Colors.dark },

  questionCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: Colors.cardBg,
    borderRadius: 10,
    padding: 14,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: Colors.border,
  },
  questionIcon: { fontSize: 16 },
  questionText: { flex: 1, fontSize: 13, color: Colors.text },
  questionArrow: { fontSize: 16, color: Colors.textMuted },
})
