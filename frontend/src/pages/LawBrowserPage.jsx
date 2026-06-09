import React, { useState, useEffect, useRef } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import Header from '../components/Header'
import Footer from '../components/Footer'
import { getChude, getDemuc, getChuong, getMuc, getDieuList } from '../services/api'
import { useBrowserStore } from '../store/browserStore'
import '../styles/LawBrowserPage.css'

// "Điều 3 Thông tư liên tịch số 01/2016/..., có hiệu lực thi hành kể từ ngày 01/03/2016"
// → "Điều 3 Luật Hôn nhân và gia đình 2016"
function formatCitation(vbqppl, demucTen) {
  if (!vbqppl || !demucTen) return null
  const dieuMatch = vbqppl.match(/Điều\s+(\d+)/)
  const yearMatch = vbqppl.match(/số\s+\d+\/(\d{4})\//)
  if (!dieuMatch || !yearMatch) return null
  return `Điều ${dieuMatch[1]} Luật ${demucTen} ${yearMatch[1]}`
}

// "Điều 8.4.TL.1.3. Thụ lý, giải quyết..." → "Thụ lý, giải quyết..."
function cleanDieuTen(ten) {
  if (!ten) return ''
  return ten.replace(/^Điều\s+[\d.A-Za-z]+\.\s*/, '').trim()
}

export default function LawBrowserPage() {
  const [searchParams] = useSearchParams()
  const autoSelectDone = useRef(false)

  const {
    selectedChude, selectedDemuc, selectedChuong, selectedMuc,
    demucs, chuongs, mucs, dieus,
    resetToChude, resetToDemuc, resetToChuong, resetToMuc,
    setDemucs, setChuongs, setMucs, setDieus
  } = useBrowserStore()

  const [chudes, setChudes] = useState([])
  const [loadingChude, setLoadingChude] = useState(true)
  const [loadingDemuc, setLoadingDemuc] = useState(false)
  const [loadingChuong, setLoadingChuong] = useState(false)
  const [loadingMuc, setLoadingMuc] = useState(false)
  const [loadingDieu, setLoadingDieu] = useState(false)

  useEffect(() => {
    getChude().then(setChudes).finally(() => setLoadingChude(false))
  }, [])

  // Auto-select từ URL params
  useEffect(() => {
    if (autoSelectDone.current || chudes.length === 0) return
    const chudeId = searchParams.get('chude_id')
    if (!chudeId) return
    const chude = chudes.find(c => String(c.id) === chudeId)
    if (!chude) return

    autoSelectDone.current = true
    const demucId = searchParams.get('demuc_id')
    const chuongId = searchParams.get('chuong_id')

    resetToChude(chude)
    setLoadingDemuc(true)
    getDemuc(chude.id).then(demucs => {
      setDemucs(demucs)
      setLoadingDemuc(false)
      if (!demucId) return
      const demuc = demucs.find(d => String(d.id) === demucId)
      if (!demuc) return

      resetToDemuc(demuc)
      setLoadingChuong(true)
      getChuong(demuc.id).then(async chuongs => {
        setChuongs(chuongs)
        setLoadingChuong(false)
        if (!chuongId) {
          if (chuongs.length === 0) {
            setLoadingDieu(true)
            getDieuList({ demucId: demuc.id }).then(setDieus).finally(() => setLoadingDieu(false))
          }
          return
        }
        const chuong = chuongs.find(c => c.mapc === decodeURIComponent(chuongId))
        if (!chuong) return
        resetToChuong(chuong)
        await loadMucOrDieu(chuong)
      }).catch(() => setLoadingChuong(false))
    }).catch(() => setLoadingDemuc(false))
  }, [chudes, searchParams])

  // Sau khi chọn chương: fetch mục, nếu có thì hiện cột mục, nếu không thì load điều
  const loadMucOrDieu = async (chuong) => {
    setLoadingMuc(true)
    try {
      const mucData = await getMuc(chuong.mapc)
      setMucs(mucData)
      setLoadingMuc(false)
      if (mucData.length === 0) {
        // Không có mục → load điều thẳng
        setLoadingDieu(true)
        const dieuData = await getDieuList({ chuongId: chuong.mapc })
        setDieus(dieuData)
        setLoadingDieu(false)
      }
      // Có mục → chờ user chọn mục
    } catch {
      setLoadingMuc(false)
    }
  }

  const handleSelectChude = async (chude) => {
    if (selectedChude?.id === chude.id) return
    resetToChude(chude)
    setLoadingDemuc(true)
    try {
      setDemucs(await getDemuc(chude.id))
    } finally {
      setLoadingDemuc(false)
    }
  }

  const handleSelectDemuc = async (demuc) => {
    if (selectedDemuc?.id === demuc.id) return
    resetToDemuc(demuc)
    setLoadingChuong(true)
    try {
      const data = await getChuong(demuc.id)
      setChuongs(data)
      if (data.length === 0) {
        setLoadingDieu(true)
        setDieus(await getDieuList({ demucId: demuc.id }))
        setLoadingDieu(false)
      }
    } finally {
      setLoadingChuong(false)
    }
  }

  const handleSelectChuong = async (chuong) => {
    if (selectedChuong?.mapc === chuong.mapc) return
    resetToChuong(chuong)
    await loadMucOrDieu(chuong)
  }

  const handleSelectMuc = async (muc) => {
    if (selectedMuc?.mapc === muc.mapc) return
    resetToMuc(muc)
    setLoadingDieu(true)
    try {
      setDieus(await getDieuList({ mucId: muc.mapc }))
    } finally {
      setLoadingDieu(false)
    }
  }

  // Có hiện cột Mục không: khi chương đã chọn VÀ (đang load mục hoặc có mục)
  const showMucCol = selectedChuong && (loadingMuc || mucs.length > 0)

  return (
    <div className="law-browser-page">
      <Header />

      <div className="browser-hero">
        <div className="browser-hero-inner">
          <div className="browser-breadcrumb">
            <span>📚</span>
            <span>Pháp điển</span>
          </div>
          <h1>Tra cứu Pháp điển</h1>
          <p>Duyệt toàn bộ hệ thống văn bản pháp luật Việt Nam theo cấu trúc phân cấp</p>
        </div>
      </div>

      <div className="browser-layout">

        {/* Column 1: Chủ đề */}
        <div className="browser-col">
          <div className="col-header">
            <span className="col-icon">📂</span>
            <span>Chủ đề</span>
            {chudes.length > 0 && <span className="col-count">{chudes.length}</span>}
          </div>
          <div className="col-body">
            {loadingChude ? (
              <div className="col-loading">Đang tải...</div>
            ) : (
              chudes.map((c) => (
                <button
                  key={c.id}
                  className={`tree-item ${selectedChude?.id === c.id ? 'active' : ''}`}
                  onClick={() => handleSelectChude(c)}
                >
                  <span className="item-stt">{c.stt}</span>
                  <span className="item-text">{c.ten}</span>
                  <span className="item-arrow">›</span>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Column 2: Đề mục */}
        <div className="browser-col">
          <div className="col-header">
            <span className="col-icon">📋</span>
            <span>Đề mục</span>
            {demucs.length > 0 && <span className="col-count">{demucs.length}</span>}
          </div>
          <div className="col-body">
            {!selectedChude ? (
              <div className="col-empty">← Chọn chủ đề</div>
            ) : loadingDemuc ? (
              <div className="col-loading">Đang tải...</div>
            ) : demucs.length === 0 ? (
              <div className="col-empty">Không có đề mục</div>
            ) : (
              demucs.map((d) => (
                <button
                  key={d.id}
                  className={`tree-item ${selectedDemuc?.id === d.id ? 'active' : ''}`}
                  onClick={() => handleSelectDemuc(d)}
                >
                  <span className="item-stt">{d.stt}</span>
                  <span className="item-text">{d.ten}</span>
                  <span className="item-arrow">›</span>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Column 3: Chương */}
        <div className="browser-col">
          <div className="col-header">
            <span className="col-icon">📑</span>
            <span>Chương</span>
            {chuongs.length > 0 && <span className="col-count">{chuongs.length}</span>}
          </div>
          <div className="col-body">
            {!selectedDemuc ? (
              <div className="col-empty">← Chọn đề mục</div>
            ) : loadingChuong ? (
              <div className="col-loading">Đang tải...</div>
            ) : chuongs.length === 0 ? (
              <div className="col-empty">Không có chương</div>
            ) : (
              chuongs.map((c) => (
                <button
                  key={c.mapc}
                  className={`tree-item ${selectedChuong?.mapc === c.mapc ? 'active' : ''}`}
                  onClick={() => handleSelectChuong(c)}
                >
                  {c.chimuc && <span className="item-chimuc">{c.chimuc}</span>}
                  <span className="item-text">{c.ten}</span>
                  <span className="item-arrow">›</span>
                </button>
              ))
            )}
          </div>
        </div>

        {/* Column 4: Mục (chỉ hiện khi chương có mục) */}
        {showMucCol && (
          <div className="browser-col">
            <div className="col-header">
              <span className="col-icon">🗂️</span>
              <span>Mục</span>
              {mucs.length > 0 && <span className="col-count">{mucs.length}</span>}
            </div>
            <div className="col-body">
              {loadingMuc ? (
                <div className="col-loading">Đang tải...</div>
              ) : (
                mucs.map((m) => (
                  <button
                    key={m.mapc}
                    className={`tree-item ${selectedMuc?.mapc === m.mapc ? 'active' : ''}`}
                    onClick={() => handleSelectMuc(m)}
                  >
                    <span className="item-chimuc">{m.chimuc}</span>
                    <span className="item-text">{m.ten}</span>
                    <span className="item-arrow">›</span>
                  </button>
                ))
              )}
            </div>
          </div>
        )}

        {/* Column cuối: Điều luật */}
        <div className="browser-col browser-col-dieu">
          <div className="col-header">
            <span className="col-icon">📄</span>
            <span>Điều luật</span>
            {dieus.length > 0 && <span className="col-count">{dieus.length}</span>}
          </div>
          <div className="col-body">
            {!selectedDemuc ? (
              <div className="col-empty">← Chọn đề mục hoặc chương</div>
            ) : loadingDieu ? (
              <div className="col-loading">Đang tải...</div>
            ) : dieus.length === 0 ? (
              showMucCol && !selectedMuc ? (
                <div className="col-empty">← Chọn mục</div>
              ) : selectedChuong || chuongs.length === 0 ? (
                <div className="col-empty">Không có điều luật</div>
              ) : (
                <div className="col-empty">← Chọn chương</div>
              )
            ) : (
              dieus.map((d) => (
                <Link
                  key={d.mapc}
                  to={`/phap-dien/dieu/${encodeURIComponent(d.mapc)}`}
                  className="dieu-item"
                >
                  <span className="dieu-num">
                    {formatCitation(d.vbqppl, selectedDemuc?.ten) || `Điều ${d.chimuc}`}
                  </span>
                  <span className="dieu-text">{cleanDieuTen(d.ten)}</span>
                </Link>
              ))
            )}
          </div>
        </div>

      </div>

      <Footer />
    </div>
  )
}
