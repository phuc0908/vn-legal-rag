import React, { useEffect, useState } from 'react'
import {
  View, Text, StyleSheet, FlatList, TouchableOpacity,
  ActivityIndicator, ScrollView,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { useNavigation } from '@react-navigation/native'
import { NativeStackNavigationProp } from '@react-navigation/native-stack'
import { getChude, getDemuc, getChuong, getDieuList } from '../services/api'
import { Colors } from '../theme/colors'
import { Chude, Demuc, Chuong, DieuItem, LawStackParamList } from '../types'

type NavProp = NativeStackNavigationProp<LawStackParamList, 'LawBrowser'>

type Level = 'chude' | 'demuc' | 'chuong' | 'dieu'

export default function LawBrowserScreen() {
  const navigation = useNavigation<NavProp>()

  // Data
  const [chudes, setChudes] = useState<Chude[]>([])
  const [demucs, setDemucs] = useState<Demuc[]>([])
  const [chuongs, setChuongs] = useState<Chuong[]>([])
  const [dieus, setDieus] = useState<DieuItem[]>([])

  // Selection
  const [selectedChude, setSelectedChude] = useState<Chude | null>(null)
  const [selectedDemuc, setSelectedDemuc] = useState<Demuc | null>(null)
  const [selectedChuong, setSelectedChuong] = useState<Chuong | null>(null)

  // Loading
  const [loading, setLoading] = useState(false)
  const [level, setLevel] = useState<Level>('chude')

  // Breadcrumb
  const breadcrumb = [
    selectedChude ? selectedChude.ten : null,
    selectedDemuc ? selectedDemuc.ten : null,
    selectedChuong ? selectedChuong.ten : null,
  ].filter(Boolean)

  useEffect(() => {
    setLoading(true)
    getChude()
      .then(setChudes)
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handleSelectChude = async (chude: Chude) => {
    setSelectedChude(chude)
    setSelectedDemuc(null)
    setSelectedChuong(null)
    setDemucs([])
    setChuongs([])
    setDieus([])
    setLoading(true)
    try {
      const data = await getDemuc(chude.id)
      setDemucs(data)
      setLevel('demuc')
    } finally {
      setLoading(false)
    }
  }

  const handleSelectDemuc = async (demuc: Demuc) => {
    setSelectedDemuc(demuc)
    setSelectedChuong(null)
    setChuongs([])
    setDieus([])
    setLoading(true)
    try {
      const chuongData = await getChuong(demuc.id)
      if (chuongData.length > 0) {
        setChuongs(chuongData)
        setLevel('chuong')
      } else {
        // No chapters → load articles directly
        const dieuData = await getDieuList({ demucId: demuc.id })
        setDieus(dieuData)
        setLevel('dieu')
      }
    } finally {
      setLoading(false)
    }
  }

  const handleSelectChuong = async (chuong: Chuong) => {
    setSelectedChuong(chuong)
    setDieus([])
    setLoading(true)
    try {
      const data = await getDieuList({ chuongId: chuong.mapc })
      setDieus(data)
      setLevel('dieu')
    } finally {
      setLoading(false)
    }
  }

  const goBack = () => {
    if (level === 'dieu') {
      if (selectedChuong) {
        setLevel('chuong')
        setSelectedChuong(null)
        setDieus([])
      } else {
        setLevel('demuc')
        setSelectedDemuc(null)
        setDieus([])
      }
    } else if (level === 'chuong') {
      setLevel('demuc')
      setSelectedDemuc(null)
      setChuongs([])
    } else if (level === 'demuc') {
      setLevel('chude')
      setSelectedChude(null)
      setDemucs([])
    }
  }

  // Render list items
  const renderChude = ({ item }: { item: Chude }) => (
    <TouchableOpacity
      style={styles.listItem}
      onPress={() => handleSelectChude(item)}
      activeOpacity={0.7}
    >
      <View style={styles.itemIcon}>
        <Text style={styles.itemIconText}>📂</Text>
      </View>
      <Text style={styles.itemText} numberOfLines={2}>{item.ten}</Text>
      <Text style={styles.itemArrow}>›</Text>
    </TouchableOpacity>
  )

  const renderDemuc = ({ item }: { item: Demuc }) => (
    <TouchableOpacity
      style={styles.listItem}
      onPress={() => handleSelectDemuc(item)}
      activeOpacity={0.7}
    >
      <View style={[styles.itemIcon, { backgroundColor: '#eef6ff' }]}>
        <Text style={styles.itemIconText}>📋</Text>
      </View>
      <Text style={styles.itemText} numberOfLines={2}>{item.ten}</Text>
      <Text style={styles.itemArrow}>›</Text>
    </TouchableOpacity>
  )

  const renderChuong = ({ item }: { item: Chuong }) => (
    <TouchableOpacity
      style={styles.listItem}
      onPress={() => handleSelectChuong(item)}
      activeOpacity={0.7}
    >
      <View style={[styles.itemIcon, { backgroundColor: '#f0fff4' }]}>
        <Text style={styles.itemIconText}>📑</Text>
      </View>
      <Text style={styles.itemText} numberOfLines={2}>{item.ten}</Text>
      <Text style={styles.itemArrow}>›</Text>
    </TouchableOpacity>
  )

  const renderDieu = ({ item }: { item: DieuItem }) => (
    <TouchableOpacity
      style={styles.dieuItem}
      onPress={() => navigation.navigate('DieuDetail', { mapc: item.mapc })}
      activeOpacity={0.7}
    >
      <View style={styles.dieuLeft}>
        <Text style={styles.dieuMacp}>{item.chimuc || item.mapc}</Text>
        <Text style={styles.dieuTitle} numberOfLines={2}>{item.ten}</Text>
        {item.vbqppl && (
          <Text style={styles.dieuVbqppl} numberOfLines={1}>{item.vbqppl}</Text>
        )}
      </View>
      <Text style={styles.itemArrow}>›</Text>
    </TouchableOpacity>
  )

  // Level titles
  const levelTitles: Record<Level, string> = {
    chude: 'Chọn chủ đề',
    demuc: selectedChude?.ten || 'Chọn đề mục',
    chuong: selectedDemuc?.ten || 'Chọn chương',
    dieu: selectedChuong?.ten || selectedDemuc?.ten || 'Danh sách điều',
  }

  return (
    <SafeAreaView style={styles.safe} edges={['bottom']}>
      {/* Breadcrumb / Back nav */}
      {level !== 'chude' && (
        <View style={styles.breadcrumbBar}>
          <TouchableOpacity style={styles.backBtn} onPress={goBack}>
            <Text style={styles.backBtnText}>‹ Quay lại</Text>
          </TouchableOpacity>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.breadcrumbScroll}>
            {breadcrumb.map((b, i) => (
              <React.Fragment key={i}>
                {i > 0 && <Text style={styles.breadcrumbSep}> › </Text>}
                <Text style={styles.breadcrumbItem} numberOfLines={1}>{b}</Text>
              </React.Fragment>
            ))}
          </ScrollView>
        </View>
      )}

      {/* Level title */}
      <View style={styles.levelHeader}>
        <Text style={styles.levelTitle}>{levelTitles[level]}</Text>
      </View>

      {loading ? (
        <View style={styles.center}>
          <ActivityIndicator size="large" color={Colors.primary} />
        </View>
      ) : (
        <>
          {level === 'chude' && (
            <FlatList
              data={chudes}
              keyExtractor={(item) => String(item.id)}
              renderItem={renderChude}
              contentContainerStyle={styles.listContent}
              showsVerticalScrollIndicator={false}
            />
          )}
          {level === 'demuc' && (
            <FlatList
              data={demucs}
              keyExtractor={(item) => String(item.id)}
              renderItem={renderDemuc}
              contentContainerStyle={styles.listContent}
              showsVerticalScrollIndicator={false}
            />
          )}
          {level === 'chuong' && (
            <FlatList
              data={chuongs}
              keyExtractor={(item) => item.mapc}
              renderItem={renderChuong}
              contentContainerStyle={styles.listContent}
              showsVerticalScrollIndicator={false}
            />
          )}
          {level === 'dieu' && (
            <FlatList
              data={dieus}
              keyExtractor={(item) => item.mapc}
              renderItem={renderDieu}
              contentContainerStyle={styles.listContent}
              showsVerticalScrollIndicator={false}
            />
          )}
        </>
      )}
    </SafeAreaView>
  )
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.background },

  breadcrumbBar: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: Colors.border,
    gap: 8,
  },
  backBtn: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    flexShrink: 0,
  },
  backBtnText: { fontSize: 14, color: Colors.primary, fontWeight: '600' },
  breadcrumbScroll: { flex: 1 },
  breadcrumbItem: { fontSize: 12, color: Colors.textSecondary, maxWidth: 160 },
  breadcrumbSep: { fontSize: 12, color: Colors.textMuted },

  levelHeader: {
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: Colors.primaryLight,
    borderBottomWidth: 1,
    borderBottomColor: Colors.primaryBorder,
  },
  levelTitle: { fontSize: 15, fontWeight: '700', color: Colors.primary },

  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },

  listContent: { padding: 12, gap: 8 },

  listItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.cardBg,
    borderRadius: 10,
    padding: 14,
    borderWidth: 1,
    borderColor: Colors.border,
    gap: 12,
  },
  itemIcon: {
    width: 36,
    height: 36,
    borderRadius: 8,
    backgroundColor: '#fff5f5',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  itemIconText: { fontSize: 18 },
  itemText: { flex: 1, fontSize: 14, color: Colors.dark, fontWeight: '500', lineHeight: 20 },
  itemArrow: { fontSize: 20, color: Colors.textMuted, flexShrink: 0 },

  dieuItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: Colors.cardBg,
    borderRadius: 10,
    padding: 14,
    borderWidth: 1,
    borderColor: Colors.border,
    gap: 8,
  },
  dieuLeft: { flex: 1 },
  dieuMacp: {
    fontSize: 11,
    fontWeight: '700',
    color: Colors.primary,
    marginBottom: 3,
    textTransform: 'uppercase',
  },
  dieuTitle: { fontSize: 13, color: Colors.dark, fontWeight: '600', lineHeight: 18, marginBottom: 3 },
  dieuVbqppl: { fontSize: 11, color: Colors.textMuted, fontStyle: 'italic' },
})
