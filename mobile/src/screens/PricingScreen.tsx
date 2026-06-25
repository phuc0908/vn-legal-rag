import React, { useState, useEffect } from 'react'
import {
  View, Text, TouchableOpacity, StyleSheet,
  ScrollView, ActivityIndicator, Alert, Linking,
} from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { SafeAreaView } from 'react-native-safe-area-context'
import { useNavigation } from '@react-navigation/native'
import { NativeStackNavigationProp } from '@react-navigation/native-stack'
import { getPlans, createPayment, getMySubscription } from '../services/api'
import { useAuthStore } from '../store/authStore'
import { Colors } from '../theme/colors'
import { RootStackParamList } from '../types'

type NavProp = NativeStackNavigationProp<RootStackParamList>

interface PlanInfo {
  id: string
  name: string
  amount: number
  days: number
  daily_limit: number
}

const PLAN_ORDER = ['free', 'plus', 'pro']
const PLAN_COLORS: Record<string, string> = { free: '#6b7280', plus: '#2980b9', pro: '#f39c12' }
const PLAN_FEATURES: Record<string, string[]> = {
  free: ['20 câu hỏi / ngày', 'Tra cứu pháp điển', 'Lưu điều luật yêu thích', 'Lịch sử xem'],
  plus: ['100 câu hỏi / ngày', 'Tất cả tính năng Free', 'Ưu tiên xử lý câu hỏi', 'Hỗ trợ đa chủ đề luật'],
  pro: ['Không giới hạn câu hỏi', 'Tất cả tính năng Plus', 'Lộ trình thủ tục ly hôn', 'Tải biểu mẫu pháp lý'],
}

export default function PricingScreen() {
  const navigation = useNavigation<NavProp>()
  const { isAuthenticated } = useAuthStore()

  const [plans, setPlans] = useState<Record<string, PlanInfo>>({})
  const [currentPlan, setCurrentPlan] = useState<string>('free')
  const [loading, setLoading] = useState(true)
  const [purchasing, setPurchasing] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([
      getPlans(),
      isAuthenticated ? getMySubscription() : Promise.resolve(null),
    ])
      .then(([p, sub]) => {
        setPlans(p)
        if (sub) setCurrentPlan(sub.plan)
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [isAuthenticated])

  const handlePurchase = async (planId: string) => {
    if (!isAuthenticated) {
      Alert.alert('Yêu cầu đăng nhập', 'Vui lòng đăng nhập để mua gói.', [
        { text: 'Hủy', style: 'cancel' },
        { text: 'Đăng nhập', onPress: () => navigation.navigate('Login') },
      ])
      return
    }
    if (planId === currentPlan) return

    setPurchasing(planId)
    try {
      const result = await createPayment(planId)
      await Linking.openURL(result.checkout_url)
      Alert.alert(
        'Thanh toán',
        'Sau khi thanh toán xong, quay lại ứng dụng và vào Tài khoản để kiểm tra gói của bạn.',
        [{ text: 'OK' }]
      )
    } catch (err: any) {
      Alert.alert('Lỗi', err.response?.data?.detail || 'Không thể tạo liên kết thanh toán. Thử lại sau.')
    } finally {
      setPurchasing(null)
    }
  }

  const freePlan: PlanInfo = { id: 'free', name: 'Gói Miễn phí', amount: 0, days: 0, daily_limit: 20 }
  const allPlans: PlanInfo[] = [
    freePlan,
    ...PLAN_ORDER.filter((k) => k !== 'free' && plans[k]).map((k) => plans[k]),
  ]

  return (
    <SafeAreaView style={styles.safe} edges={['top']}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backBtn}>
          <Text style={styles.backText}>← Quay lại</Text>
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Gói dịch vụ</Text>
        <View style={{ width: 70 }} />
      </View>

      <ScrollView contentContainerStyle={styles.container} showsVerticalScrollIndicator={false}>
        <View style={styles.topSection}>
          <Text style={styles.topTitle}>Nâng cấp trải nghiệm</Text>
          <Text style={styles.topSub}>Chọn gói phù hợp với nhu cầu của bạn</Text>
        </View>

        {loading ? (
          <ActivityIndicator size="large" color={Colors.primary} style={{ marginTop: 40 }} />
        ) : (
          allPlans.map((plan) => {
            const isCurrent = plan.id === currentPlan
            const color = PLAN_COLORS[plan.id] ?? Colors.primary
            const features = PLAN_FEATURES[plan.id] ?? []
            const isPurchasing = purchasing === plan.id

            return (
              <View
                key={plan.id}
                style={[styles.planCard, isCurrent && { borderColor: color, borderWidth: 2 }]}
              >
                {isCurrent && (
                  <View style={[styles.currentBadge, { backgroundColor: color }]}>
                    <Text style={styles.currentBadgeText}>Gói hiện tại</Text>
                  </View>
                )}

                <View style={styles.planHeader}>
                  <View style={[styles.planIconBox, { backgroundColor: color + '20' }]}>
                    <Ionicons
                      name={plan.id === 'pro' ? 'star' : plan.id === 'plus' ? 'flash' : 'checkmark-circle'}
                      size={20}
                      color={color}
                    />
                  </View>
                  <View style={styles.planHeaderText}>
                    <Text style={[styles.planName, { color }]}>{plan.name}</Text>
                    {plan.amount > 0 ? (
                      <Text style={styles.planPrice}>
                        {plan.amount.toLocaleString('vi-VN')}đ / {plan.days} ngày
                      </Text>
                    ) : (
                      <Text style={styles.planPrice}>Miễn phí mãi mãi</Text>
                    )}
                  </View>
                </View>

                <View style={styles.featureList}>
                  {features.map((f) => (
                    <View key={f} style={styles.featureRow}>
                      <Text style={[styles.featureCheck, { color }]}>✓</Text>
                      <Text style={styles.featureText}>{f}</Text>
                    </View>
                  ))}
                </View>

                {plan.id !== 'free' && (
                  <TouchableOpacity
                    style={[
                      styles.buyBtn,
                      { backgroundColor: color },
                      isCurrent && styles.buyBtnDisabled,
                    ]}
                    onPress={() => handlePurchase(plan.id)}
                    disabled={isCurrent || isPurchasing}
                    activeOpacity={0.8}
                  >
                    {isPurchasing ? (
                      <ActivityIndicator color="#fff" />
                    ) : (
                      <Text style={styles.buyBtnText}>
                        {isCurrent ? 'Đang sử dụng' : `Mua ${plan.name}`}
                      </Text>
                    )}
                  </TouchableOpacity>
                )}
              </View>
            )
          })
        )}

        <Text style={styles.note}>
          * Thanh toán qua PayOS – hỗ trợ tất cả ngân hàng Việt Nam.{'\n'}
          Gói được kích hoạt ngay sau khi thanh toán thành công.
        </Text>
      </ScrollView>
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

  topSection: { alignItems: 'center', paddingVertical: 8 },
  topTitle: { fontSize: 22, fontWeight: '800', color: Colors.dark },
  topSub: { fontSize: 13, color: Colors.textMuted, marginTop: 4 },

  planCard: {
    backgroundColor: '#fff',
    borderRadius: 14,
    padding: 18,
    borderWidth: 1,
    borderColor: Colors.border,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 6,
    elevation: 2,
    gap: 12,
    overflow: 'hidden',
  },
  currentBadge: {
    position: 'absolute',
    top: 12,
    right: 12,
    paddingHorizontal: 10,
    paddingVertical: 3,
    borderRadius: 20,
  },
  currentBadgeText: { color: '#fff', fontSize: 11, fontWeight: '700' },

  planHeader: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  planIconBox: {
    width: 40, height: 40, borderRadius: 10,
    alignItems: 'center', justifyContent: 'center',
  },
  planHeaderText: { flex: 1 },
  planName: { fontSize: 17, fontWeight: '800' },
  planPrice: { fontSize: 13, color: Colors.textMuted, marginTop: 2 },

  featureList: { gap: 8 },
  featureRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 8 },
  featureCheck: { fontSize: 14, fontWeight: '800', marginTop: 1 },
  featureText: { fontSize: 13, color: Colors.text, flex: 1, lineHeight: 18 },

  buyBtn: {
    borderRadius: 10,
    paddingVertical: 13,
    alignItems: 'center',
    marginTop: 4,
  },
  buyBtnDisabled: { opacity: 0.5 },
  buyBtnText: { color: '#fff', fontSize: 14, fontWeight: '700' },

  note: {
    fontSize: 12,
    color: Colors.textMuted,
    textAlign: 'center',
    lineHeight: 18,
    paddingHorizontal: 8,
  },
})
