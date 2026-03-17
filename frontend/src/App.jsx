import React from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import HomePage from './pages/HomePage'
import SearchPage from './pages/SearchPage'
import ChatPage from './pages/ChatPage'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/tim-kiem" element={<SearchPage />} />
        <Route path="/tu-van" element={<ChatPage />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
