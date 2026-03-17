import React, { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import '../styles/Header.css'

export default function Header() {
  const location = useLocation()
  const [menuOpen, setMenuOpen] = useState(false)

  const navLinks = [
    { to: '/', label: 'Trang chủ' },
    { to: '/tim-kiem', label: 'Tra cứu văn bản' },
    { to: '/tu-van', label: 'Tư vấn AI' },
  ]

  return (
    <header className="site-header">
      <div className="header-inner">
        <Link to="/" className="header-logo">
          <span className="logo-icon">⚖️</span>
          <div className="logo-text">
            <span className="logo-main">Pháp Lý Việt Nam</span>
            <span className="logo-sub">Hệ thống tra cứu pháp luật</span>
          </div>
        </Link>

        <nav className={`header-nav ${menuOpen ? 'open' : ''}`}>
          {navLinks.map((link) => (
            <Link
              key={link.to}
              to={link.to}
              className={`nav-link ${location.pathname === link.to ? 'active' : ''}`}
              onClick={() => setMenuOpen(false)}
            >
              {link.label}
            </Link>
          ))}
        </nav>

        <Link to="/tu-van" className="header-cta">
          Tư vấn ngay
        </Link>

        <button className="mobile-menu-btn" onClick={() => setMenuOpen(!menuOpen)}>
          <span></span>
          <span></span>
          <span></span>
        </button>
      </div>
    </header>
  )
}
