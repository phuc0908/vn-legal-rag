import React, { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import ThemeToggle from './ThemeToggle'
import '../styles/Header.css'

export default function Header() {
  const location = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)
  const { isAuthenticated, user, logout } = useAuthStore()

  const navLinks = [
    { to: '/', label: 'Trang chủ' },
    { to: '/phap-dien', label: 'Pháp điển' },
    { to: '/tu-van', label: 'Tư vấn AI' },
    { to: '/bang-gia', label: 'Bảng giá' },
  ]

  const isFreeUser = isAuthenticated && (!user?.subscription_plan || user.subscription_plan === 'free')

  return (
    <header className="site-header">
      <div className="header-inner">
        <Link to="/" className="header-logo">
          <span className="logo-icon">⚖️</span>
          <div className="logo-text">
            <span className="logo-main">VN Legal RAG</span>
            <span className="logo-sub">Hệ thống Tư vấn Pháp luật AI</span>
          </div>
        </Link>

        <nav className={`header-nav ${menuOpen ? 'open' : ''}`}>
          {navLinks.map((link) => {
            const isActive = link.to === '/' 
              ? location.pathname === '/' 
              : location.pathname.startsWith(link.to)
            
            return (
              <Link
                key={link.to}
                to={link.to}
                className={`nav-link ${isActive ? 'active' : ''}`}
                onClick={() => setMenuOpen(false)}
              >
                {link.label}
              </Link>
            )
          })}
        </nav>

        <div className="header-actions">
          <ThemeToggle />
          <Link
            to="/da-luu"
            className={`saved-link ${location.pathname.startsWith('/da-luu') ? 'active' : ''}`}
            title="Điều luật đã lưu & lịch sử xem"
          >
            ★ Đã lưu
          </Link>
          {isFreeUser && (
            <Link to="/bang-gia" className="upgrade-btn">✦ Nâng cấp</Link>
          )}
          {isAuthenticated ? (
            <div className="user-profile">
              {user?.is_admin && (
                <Link
                  to="/admin"
                  className={`admin-link ${location.pathname.startsWith('/admin') ? 'active' : ''}`}
                >
                  Admin
                </Link>
              )}
              <Link
                to="/ho-so"
                className={`user-name ${location.pathname.startsWith('/ho-so') ? 'active' : ''}`}
              >
                {user?.full_name || user?.username}
              </Link>
              <button className="logout-btn" onClick={logout}>Đăng xuất</button>
            </div>
          ) : (
            <Link to="/login" className="login-btn">Đăng nhập</Link>
          )}
        </div>

        <button className="mobile-menu-btn" onClick={() => setMenuOpen(!menuOpen)}>
          <span></span>
          <span></span>
          <span></span>
        </button>
      </div>
    </header>
  )
}
