import React from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import HomePage from './pages/HomePage'
import SearchPage from './pages/SearchPage'
import ChatPage from './pages/ChatPage'
import LawBrowserPage from './pages/LawBrowserPage'
import DieuDetailPage from './pages/DieuDetailPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/tim-kiem" element={<SearchPage />} />
        <Route path="/tu-van" element={<ChatPage />} />
        <Route path="/phap-dien" element={<LawBrowserPage />} />
        <Route path="/phap-dien/dieu/:mapc" element={<DieuDetailPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
