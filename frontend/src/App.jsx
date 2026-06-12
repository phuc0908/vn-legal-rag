import React, { useEffect } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import HomePage from './pages/HomePage'
import SearchPage from './pages/SearchPage'
import ChatPage from './pages/ChatPage'
import LawBrowserPage from './pages/LawBrowserPage'
import DieuDetailPage from './pages/DieuDetailPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import SavedPage from './pages/SavedPage'
import ProfilePage from './pages/ProfilePage'
import AdminPage from './pages/AdminPage'
import PricingPage from './pages/PricingPage'
import PaymentResultPage from './pages/PaymentResultPage'
import { useThemeStore } from './store/themeStore'
import './App.css'

function App() {
  const { isDark } = useThemeStore()

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light')
  }, [isDark])

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/tim-kiem" element={<SearchPage />} />
        <Route path="/tu-van" element={<ChatPage />} />
        <Route path="/phap-dien" element={<LawBrowserPage />} />
        <Route path="/phap-dien/dieu/:mapc" element={<DieuDetailPage />} />
        <Route path="/da-luu" element={<SavedPage />} />
        <Route path="/ho-so" element={<ProfilePage />} />
        <Route path="/admin" element={<AdminPage />} />
        <Route path="/bang-gia" element={<PricingPage />} />
        <Route path="/payment/result" element={<PaymentResultPage />} />
        <Route path="/payment/cancel" element={<PaymentResultPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
