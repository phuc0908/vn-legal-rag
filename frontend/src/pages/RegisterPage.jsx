import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { register } from '../services/api'
import Header from '../components/Header'
import Footer from '../components/Footer'
import '../styles/AuthPages.css'

export default function RegisterPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    
    try {
      await register({ 
        username, 
        password, 
        full_name: fullName,
        email: email || undefined
      })
      setSuccess(true)
      setTimeout(() => navigate('/login'), 2000)
    } catch (err) {
      setError(err.response?.data?.detail || 'Đăng ký thất bại. Tên đăng nhập có thể đã tồn tại.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <Header />
      <div className="auth-container">
        <form className="auth-form" onSubmit={handleSubmit}>
          <h2>Đăng ký tài khoản</h2>
          <p className="auth-subtitle">Tạo tài khoản để bắt đầu trải nghiệm tư vấn cá nhân hóa</p>
          
          {error && <div className="auth-error">{error}</div>}
          {success && <div className="auth-success">Đăng ký thành công! Đang chuyển hướng sang đăng nhập...</div>}
          
          <div className="form-group">
            <label>Họ và tên</label>
            <input 
              type="text" 
              value={fullName} 
              onChange={e => setFullName(e.target.value)} 
              required 
              placeholder="Nhập họ và tên"
            />
          </div>

          <div className="form-group">
            <label>Tên đăng nhập</label>
            <input 
              type="text" 
              value={username} 
              onChange={e => setUsername(e.target.value)} 
              required 
              placeholder="Chọn tên đăng nhập"
            />
          </div>

          <div className="form-group">
            <label>Email (Tùy chọn)</label>
            <input 
              type="email" 
              value={email} 
              onChange={e => setEmail(e.target.value)} 
              placeholder="Nhập địa chỉ email"
            />
          </div>
          
          <div className="form-group">
            <label>Mật khẩu</label>
            <input 
              type="password" 
              value={password} 
              onChange={e => setPassword(e.target.value)} 
              required 
              placeholder="Nhập mật khẩu"
            />
          </div>
          
          <button type="submit" className="auth-submit" disabled={loading || success}>
            {loading ? 'Đang đăng ký...' : 'Đăng ký'}
          </button>
          
          <div className="auth-footer">
            Đã có tài khoản? <Link to="/login">Đăng nhập</Link>
          </div>
        </form>
      </div>
      <Footer />
    </div>
  )
}
