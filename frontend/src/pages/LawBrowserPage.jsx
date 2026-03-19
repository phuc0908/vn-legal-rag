import React, { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Header from '../components/Header'
import Footer from '../components/Footer'
import { getChude, getDemuc, getChuong, getDieuList } from '../services/api'
import { useBrowserStore } from '../store/browserStore'
import '../styles/LawBrowserPage.css'

export default function LawBrowserPage() {
  const navigate = useNavigate()

  // Global store states
  const {
    selectedChude,
    selectedDemuc,
    selectedChuong,
    demucs,
    chuongs,
    dieus,
    resetToChude,
    resetToDemuc,
    resetToChuong,
    setDemucs,
    setChuongs,
    setDieus
  } = useBrowserStore()

  const [chudes, setChudes] = useState([])
  const [loadingChude, setLoadingChude] = useState(true)
  const [loadingDemuc, setLoadingDemuc] = useState(false)
  const [loadingChuong, setLoadingChuong] = useState(false)
  const [loadingDieu, setLoadingDieu] = useState(false)

  // Load all chủ đề on mount
  useEffect(() => {
    getChude()
      .then(setChudes)
      .finally(() => setLoadingChude(false))
  }, [])

  const handleSelectChude = async (chude) => {
    if (selectedChude?.id === chude.id) return
    resetToChude(chude)
    
    setLoadingDemuc(true)
    try {
      const data = await getDemuc(chude.id)
      setDemucs(data)
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
      // If no chapters, load articles directly
      if (data.length === 0) {
        setLoadingDieu(true)
        try {
          const dieuData = await getDieuList({ demucId: demuc.id })
          setDieus(dieuData)
        } finally {
          setLoadingDieu(false)
        }
      }
    } finally {
      setLoadingChuong(false)
    }
  }

  const handleSelectChuong = async (chuong) => {
    if (selectedChuong?.mapc === chuong.mapc) return
    resetToChuong(chuong)
    
    setLoadingDieu(true)
    try {
      const data = await getDieuList({ chuongId: chuong.mapc })
      setDieus(data)
    } finally {
      setLoadingDieu(false)
    }
  }

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

        {/* Column 4: Điều */}
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
              selectedChuong || chuongs.length === 0 ? (
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
                  <span className="dieu-num">Điều {d.chimuc}</span>
                  <span className="dieu-text">{d.ten}</span>
                  {d.vbqppl && <span className="dieu-vb">{d.vbqppl}</span>}
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
