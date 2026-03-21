import React, { useState, useEffect } from 'react'
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  Modal, FlatList, Platform,
} from 'react-native'
import { getChude } from '../services/api'
import { Colors } from '../theme/colors'
import { Chude } from '../types'

interface Props {
  onSend: (text: string, chuDeId: string | null) => void
  loading: boolean
  disabled?: boolean
}

export default function InputArea({ onSend, loading, disabled }: Props) {
  const [input, setInput] = useState('')
  const [chudeList, setChudeList] = useState<Chude[]>([])
  const [selectedChudeId, setSelectedChudeId] = useState<string | null>(null)
  const [selectedChudeTen, setSelectedChudeTen] = useState<string>('')
  const [pickerVisible, setPickerVisible] = useState(false)

  useEffect(() => {
    getChude().then(setChudeList).catch(() => {})
  }, [])

  const handleSend = () => {
    const trimmed = input.trim()
    if (!trimmed || loading || disabled) return
    onSend(trimmed, selectedChudeId)
    setInput('')
  }

  const selectChude = (chude: Chude | null) => {
    if (chude) {
      setSelectedChudeId(String(chude.id))
      setSelectedChudeTen(chude.ten)
    } else {
      setSelectedChudeId(null)
      setSelectedChudeTen('')
    }
    setPickerVisible(false)
  }

  const placeholder = selectedChudeTen
    ? `Hỏi về "${selectedChudeTen}"...`
    : 'Hỏi về luật pháp Việt Nam...'

  return (
    <View style={styles.wrapper}>
      {/* Topic selector row */}
      <View style={styles.topicRow}>
        <Text style={styles.topicLabel}>Chủ đề:</Text>
        <TouchableOpacity
          style={[styles.topicBtn, !!selectedChudeId && styles.topicBtnActive]}
          onPress={() => setPickerVisible(true)}
          disabled={loading}
          activeOpacity={0.7}
        >
          <Text
            style={[styles.topicBtnText, !!selectedChudeId && styles.topicBtnTextActive]}
            numberOfLines={1}
          >
            {selectedChudeTen || 'Tất cả chủ đề'}
          </Text>
          <Text style={styles.topicArrow}>▾</Text>
        </TouchableOpacity>
        {!!selectedChudeId && (
          <TouchableOpacity
            style={styles.clearBtn}
            onPress={() => selectChude(null)}
            disabled={loading}
          >
            <Text style={styles.clearBtnText}>×</Text>
          </TouchableOpacity>
        )}
      </View>

      {/* Input row */}
      <View style={styles.inputRow}>
        <TextInput
          style={[styles.textInput, (loading || disabled) && styles.textInputDisabled]}
          value={input}
          onChangeText={setInput}
          placeholder={placeholder}
          placeholderTextColor={Colors.textPlaceholder}
          multiline
          maxLength={2000}
          editable={!loading && !disabled}
          onSubmitEditing={Platform.OS === 'ios' ? handleSend : undefined}
          blurOnSubmit={false}
        />
        <TouchableOpacity
          style={[
            styles.sendBtn,
            (!input.trim() || loading || disabled) && styles.sendBtnDisabled,
          ]}
          onPress={handleSend}
          disabled={!input.trim() || loading || disabled}
          activeOpacity={0.8}
        >
          <Text style={styles.sendBtnText}>{loading ? '⏳' : '➤'}</Text>
        </TouchableOpacity>
      </View>

      {/* Topic Picker Modal */}
      <Modal
        visible={pickerVisible}
        animationType="slide"
        transparent
        onRequestClose={() => setPickerVisible(false)}
      >
        <TouchableOpacity
          style={styles.modalOverlay}
          activeOpacity={1}
          onPress={() => setPickerVisible(false)}
        >
          <View style={styles.modalSheet}>
            <View style={styles.modalHandle} />
            <Text style={styles.modalTitle}>Chọn chủ đề</Text>

            {/* "Tất cả" option */}
            <TouchableOpacity
              style={[styles.optionItem, !selectedChudeId && styles.optionItemActive]}
              onPress={() => selectChude(null)}
            >
              <Text style={[styles.optionText, !selectedChudeId && styles.optionTextActive]}>
                Tất cả chủ đề
              </Text>
              {!selectedChudeId && <Text style={styles.checkmark}>✓</Text>}
            </TouchableOpacity>

            <FlatList
              data={chudeList}
              keyExtractor={(item) => String(item.id)}
              style={styles.optionList}
              renderItem={({ item }) => {
                const isActive = selectedChudeId === String(item.id)
                return (
                  <TouchableOpacity
                    style={[styles.optionItem, isActive && styles.optionItemActive]}
                    onPress={() => selectChude(item)}
                  >
                    <Text
                      style={[styles.optionText, isActive && styles.optionTextActive]}
                      numberOfLines={2}
                    >
                      {item.ten}
                    </Text>
                    {isActive && <Text style={styles.checkmark}>✓</Text>}
                  </TouchableOpacity>
                )
              }}
            />
          </View>
        </TouchableOpacity>
      </Modal>
    </View>
  )
}

const styles = StyleSheet.create({
  wrapper: {
    backgroundColor: '#fff',
    borderTopWidth: 1,
    borderTopColor: Colors.border,
    paddingHorizontal: 12,
    paddingTop: 8,
    paddingBottom: 10,
  },

  topicRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    marginBottom: 8,
  },
  topicLabel: { fontSize: 12, fontWeight: '600', color: Colors.textMuted, flexShrink: 0 },
  topicBtn: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderColor: Colors.borderDark,
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 6,
    backgroundColor: Colors.inputBg,
    gap: 4,
  },
  topicBtnActive: {
    borderColor: Colors.primary,
    backgroundColor: Colors.primaryLight,
  },
  topicBtnText: { flex: 1, fontSize: 13, color: Colors.textSecondary },
  topicBtnTextActive: { color: Colors.primary, fontWeight: '600' },
  topicArrow: { fontSize: 11, color: Colors.textMuted },

  clearBtn: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: Colors.border,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  clearBtnText: { fontSize: 16, color: Colors.textSecondary, lineHeight: 20 },

  inputRow: { flexDirection: 'row', gap: 8, alignItems: 'flex-end' },
  textInput: {
    flex: 1,
    minHeight: 42,
    maxHeight: 120,
    borderWidth: 1,
    borderColor: Colors.borderDark,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingTop: 10,
    paddingBottom: 10,
    fontSize: 14,
    color: Colors.text,
    backgroundColor: Colors.inputBg,
    textAlignVertical: 'top',
  },
  textInputDisabled: { backgroundColor: '#f3f4f6', color: Colors.textPlaceholder },

  sendBtn: {
    width: 42,
    height: 42,
    backgroundColor: Colors.primary,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  sendBtnDisabled: { backgroundColor: '#e0e0e0' },
  sendBtnText: { fontSize: 16, color: '#fff' },

  // Modal picker
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.4)',
    justifyContent: 'flex-end',
  },
  modalSheet: {
    backgroundColor: '#fff',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    paddingTop: 8,
    maxHeight: '80%',
  },
  modalHandle: {
    width: 40,
    height: 4,
    backgroundColor: Colors.border,
    borderRadius: 2,
    alignSelf: 'center',
    marginBottom: 12,
  },
  modalTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: Colors.dark,
    paddingHorizontal: 16,
    marginBottom: 8,
  },
  optionList: { maxHeight: 420 },
  optionItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 13,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
  },
  optionItemActive: { backgroundColor: Colors.primaryLight },
  optionText: { flex: 1, fontSize: 14, color: Colors.text },
  optionTextActive: { color: Colors.primary, fontWeight: '600' },
  checkmark: { fontSize: 16, color: Colors.primary, marginLeft: 8 },
})
