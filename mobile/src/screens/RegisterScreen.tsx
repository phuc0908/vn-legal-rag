import React, { useState } from 'react'
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  ScrollView, KeyboardAvoidingView, Platform, ActivityIndicator,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { NativeStackNavigationProp } from '@react-navigation/native-stack'
import { register } from '../services/api'
import { Colors } from '../theme/colors'
import { RootStackParamList } from '../types'

type Props = {
  navigation: NativeStackNavigationProp<RootStackParamList, 'Register'>
}

export default function RegisterScreen({ navigation }: Props) {
  const [fullName, setFullName] = useState('')
  const [username, setUsername] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  const handleRegister = async () => {
    if (!fullName.trim() || !username.trim() || !password.trim()) {
      setError('Vui lòng điền đầy đủ các trường bắt buộc.')
      return
    }
    setLoading(true)
    setError('')
    try {
      await register({
        username: username.trim(),
        password,
        full_name: fullName.trim(),
        email: email.trim() || undefined,
      })
      setSuccess(true)
      setTimeout(() => navigation.navigate('Login'), 2000)
    } catch (err: any) {
      setError(
        err.response?.data?.detail ||
          'Đăng ký thất bại. Tên đăng nhập có thể đã tồn tại.'
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
          <TouchableOpacity style={styles.backBtn} onPress={() => navigation.goBack()}>
            <Text style={styles.backText}>← Quay lại</Text>
          </TouchableOpacity>
          <View style={styles.logoArea}>
            <Text style={styles.logoTitle}>Tạo tài khoản</Text>
            <Text style={styles.logoSub}>Đăng ký để trải nghiệm tư vấn cá nhân hóa</Text>
          </View>

          <View style={styles.card}>
            {!!error && (
              <View style={styles.errorBox}>
                <Text style={styles.errorText}>{error}</Text>
              </View>
            )}
            {success && (
              <View style={styles.successBox}>
                <Text style={styles.successText}>
                  Đăng ký thành công! Đang chuyển hướng sang đăng nhập...
                </Text>
              </View>
            )}

            <Text style={styles.label}>Họ và tên *</Text>
            <TextInput
              style={styles.input}
              value={fullName}
              onChangeText={setFullName}
              placeholder="Nhập họ và tên"
              placeholderTextColor={Colors.textPlaceholder}
              returnKeyType="next"
            />

            <Text style={styles.label}>Tên đăng nhập *</Text>
            <TextInput
              style={styles.input}
              value={username}
              onChangeText={setUsername}
              placeholder="Chọn tên đăng nhập"
              placeholderTextColor={Colors.textPlaceholder}
              autoCapitalize="none"
              autoCorrect={false}
              returnKeyType="next"
            />

            <Text style={styles.label}>Email (Tùy chọn)</Text>
            <TextInput
              style={styles.input}
              value={email}
              onChangeText={setEmail}
              placeholder="Nhập địa chỉ email"
              placeholderTextColor={Colors.textPlaceholder}
              keyboardType="email-address"
              autoCapitalize="none"
              returnKeyType="next"
            />

            <Text style={styles.label}>Mật khẩu *</Text>
            <TextInput
              style={styles.input}
              value={password}
              onChangeText={setPassword}
              placeholder="Nhập mật khẩu"
              placeholderTextColor={Colors.textPlaceholder}
              secureTextEntry
              returnKeyType="done"
              onSubmitEditing={handleRegister}
            />

            <TouchableOpacity
              style={[styles.submitBtn, (loading || success) && styles.submitDisabled]}
              onPress={handleRegister}
              disabled={loading || success}
              activeOpacity={0.85}
            >
              {loading ? (
                <ActivityIndicator color="#fff" />
              ) : (
                <Text style={styles.submitText}>Đăng ký</Text>
              )}
            </TouchableOpacity>

            <View style={styles.footerRow}>
              <Text style={styles.footerText}>Đã có tài khoản? </Text>
              <TouchableOpacity onPress={() => navigation.navigate('Login')}>
                <Text style={styles.footerLink}>Đăng nhập</Text>
              </TouchableOpacity>
            </View>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.background },
  flex: { flex: 1 },
  container: { flexGrow: 1, padding: 24, justifyContent: 'center' },

  logoArea: { alignItems: 'center', marginBottom: 32 },

  logoTitle: { fontSize: 24, fontWeight: '800', color: Colors.dark },
  logoSub: { fontSize: 13, color: Colors.textMuted, marginTop: 4, textAlign: 'center' },

  card: {
    backgroundColor: Colors.cardBg,
    borderRadius: 16,
    padding: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.07,
    shadowRadius: 8,
    elevation: 3,
  },

  errorBox: {
    backgroundColor: '#ffeaea',
    borderRadius: 8,
    padding: 12,
    marginBottom: 16,
    borderLeftWidth: 3,
    borderLeftColor: Colors.error,
  },
  errorText: { color: Colors.error, fontSize: 13 },
  successBox: {
    backgroundColor: '#eafbea',
    borderRadius: 8,
    padding: 12,
    marginBottom: 16,
    borderLeftWidth: 3,
    borderLeftColor: Colors.success,
  },
  successText: { color: Colors.success, fontSize: 13 },

  label: { fontSize: 13, fontWeight: '600', color: Colors.textSecondary, marginBottom: 6 },
  input: {
    borderWidth: 1,
    borderColor: Colors.borderDark,
    borderRadius: 8,
    paddingHorizontal: 14,
    paddingVertical: 10,
    fontSize: 14,
    color: Colors.text,
    backgroundColor: Colors.inputBg,
    marginBottom: 16,
  },

  submitBtn: {
    backgroundColor: Colors.primary,
    borderRadius: 10,
    paddingVertical: 14,
    alignItems: 'center',
    marginTop: 4,
    marginBottom: 20,
  },
  submitDisabled: { opacity: 0.7 },
  submitText: { color: '#fff', fontSize: 15, fontWeight: '700' },

  footerRow: { flexDirection: 'row', justifyContent: 'center' },
  footerText: { fontSize: 13, color: Colors.textMuted },
  footerLink: { fontSize: 13, color: Colors.primary, fontWeight: '600' },

  backBtn: { marginBottom: 8 },
  backText: { fontSize: 14, color: Colors.textMuted },
})
