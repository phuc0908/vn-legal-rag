import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { login, getMe } from '../services/api'
import { useAuthStore } from '../store/authStore'
import Header from '../components/Header'
import Footer from '../components/Footer'
import '../styles/AuthPages.css'

export default function LoginPage() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  
  const navigate = useNavigate()
  const setAuth = useAuthStore(state => state.setAuth)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    
    try {
      const { access_token } = await login(username, password)
      
      // 1. First set the token so interceptors can use it
      setAuth(null, access_token) // Temporarily set token without user info
      
      // 2. Then fetch user profile
      try {
        const user = await getMe()
        setAuth(user, access_token) // Update with full user info
      } catch (meError) {
        console.error("Failed to fetch user profile after login:", meError)
        // We still have the token, so we are technically authenticated
        // The user might just not have a profile yet, or there was a temporary issue.
        // We proceed with the token, but without user details.
      }
      
      navigate('/tu-van')
    } catch (err) {
      setError(err.response?.data?.detail || 'Đăng nhập thất bại. Vui lòng kiểm tra lại thông tin.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <Header />
      <div className="auth-container">
        <form className="auth-form" onSubmit={handleSubmit}>
          <h2>Đăng nhập</h2>
          <p className="auth-subtitle">Truy cập để lưu lại lịch sử tư vấn của bạn</p>
          
          {error && <div className="auth-error">{error}</div>}
          
          <div className="form-group">
            <label>Tên đăng nhập</label>
            <input 
              type="text" 
              value={username} 
              onChange={e => setUsername(e.target.value)} 
              required 
              placeholder="Nhập tên đăng nhập"
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
          
          <button type="submit" className="auth-submit" disabled={loading}>
            {loading ? 'Đang xử lý...' : 'Đăng nhập'}
          </button>
          
          <div className="auth-footer">
            Chưa có tài khoản? <Link to="/register">Đăng ký ngay</Link>
          </div>
        </form>
      </div>
      <Footer />
    </div>
  )
}
