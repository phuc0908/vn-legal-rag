import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import Header from '../components/Header'
import Footer from '../components/Footer'
import { getBookmarks, getHistory, getUserConversations, updateProfile, changePassword, uploadAvatar } from '../services/api'
import { Link } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import '../styles/ProfilePage.css'

function Avatar({ name, avatarUrl, onUpload, uploading }) {
  const initials = name
    ? name.trim().split(' ').slice(-2).map(w => w[0].toUpperCase()).join('')
    : '?'

  const handleFileChange = (e) => {
    const file = e.target.files[0]
    if (file) onUpload(file)
    e.target.value = ''
  }

  return (
    <label className="profile-avatar-wrap" title="Nhấn để đổi ảnh đại diện">
      <input
        type="file"
        accept="image/jpeg,image/png,image/webp,image/gif"
        className="avatar-file-input"
        onChange={handleFileChange}
        disabled={uploading}
      />
      {avatarUrl ? (
        <img src={avatarUrl} alt={name} className="profile-avatar profile-avatar-img" />
      ) : (
        <div className="profile-avatar">{initials}</div>
      )}
      <div className="avatar-overlay">
        {uploading ? '...' : 'Đổi ảnh'}
      </div>
    </label>
  )
}

function StatCard({ icon, label, value, loading }) {
  return (
    <div className="stat-card">
      <span className="stat-icon">{icon}</span>
      <span className="stat-value">{loading ? '—' : value}</span>
      <span className="stat-label">{label}</span>
    </div>
  )
}

export default function ProfilePage() {
  const { isAuthenticated, user, updateUser, logout } = useAuthStore()
  const navigate = useNavigate()

  const [stats, setStats] = useState({ bookmarks: 0, history: 0, conversations: 0 })
  const [statsLoading, setStatsLoading] = useState(true)

  const [avatarUploading, setAvatarUploading] = useState(false)
  const [avatarError, setAvatarError] = useState('')

  // Edit profile state
  const [editMode, setEditMode] = useState(false)
  const [fullName, setFullName] = useState(user?.full_name || '')
  const [email, setEmail] = useState(user?.email || '')
  const [profileSaving, setProfileSaving] = useState(false)
  const [profileMsg, setProfileMsg] = useState(null)

  // Change password state
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [pwSaving, setPwSaving] = useState(false)
  const [pwMsg, setPwMsg] = useState(null)

  useEffect(() => {
    if (!isAuthenticated) {
      navigate('/login')
      return
    }
    Promise.all([
      getBookmarks().catch(() => []),
      getHistory().catch(() => []),
      getUserConversations().catch(() => []),
    ]).then(([bm, hist, convs]) => {
      setStats({ bookmarks: bm.length, history: hist.length, conversations: convs.length })
    }).finally(() => setStatsLoading(false))
  }, [isAuthenticated, navigate])

  const handleAvatarUpload = async (file) => {
    setAvatarUploading(true)
    setAvatarError('')
    try {
      const updated = await uploadAvatar(file)
      updateUser(updated)
    } catch (err) {
      setAvatarError(err.response?.data?.detail || 'Upload ảnh thất bại.')
    } finally {
      setAvatarUploading(false)
    }
  }

  const handleSaveProfile = async (e) => {
    e.preventDefault()
    setProfileSaving(true)
    setProfileMsg(null)
    try {
      const updated = await updateProfile({
        full_name: fullName || null,
        email: email || null,
      })
      updateUser(updated)
      setProfileMsg({ type: 'success', text: 'Cập nhật thông tin thành công.' })
      setEditMode(false)
    } catch (err) {
      setProfileMsg({ type: 'error', text: err.response?.data?.detail || 'Cập nhật thất bại.' })
    } finally {
      setProfileSaving(false)
    }
  }

  const handleChangePassword = async (e) => {
    e.preventDefault()
    if (newPassword !== confirmPassword) {
      setPwMsg({ type: 'error', text: 'Mật khẩu mới không khớp.' })
      return
    }
    if (newPassword.length < 6) {
      setPwMsg({ type: 'error', text: 'Mật khẩu mới phải có ít nhất 6 ký tự.' })
      return
    }
    setPwSaving(true)
    setPwMsg(null)
    try {
      await changePassword(currentPassword, newPassword)
      setPwMsg({ type: 'success', text: 'Đổi mật khẩu thành công.' })
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err) {
      setPwMsg({ type: 'error', text: err.response?.data?.detail || 'Đổi mật khẩu thất bại.' })
    } finally {
      setPwSaving(false)
    }
  }

  const handleCancelEdit = () => {
    setFullName(user?.full_name || '')
    setEmail(user?.email || '')
    setProfileMsg(null)
    setEditMode(false)
  }

  if (!isAuthenticated) return null

  return (
    <div className="profile-page">
      <Header />
      <div className="profile-body">

        {/* ── Hero card ── */}
        <div className="profile-hero">
          <Avatar
            name={user?.full_name || user?.username}
            avatarUrl={user?.avatar_url}
            onUpload={handleAvatarUpload}
            uploading={avatarUploading}
          />
          <div className="profile-hero-info">
            {avatarError && <p className="avatar-error">{avatarError}</p>}
            <h1>{user?.full_name || user?.username}</h1>
            <span className="profile-username">@{user?.username}</span>
            {user?.email && <span className="profile-email">{user.email}</span>}
          </div>
          {!editMode && (
            <button className="edit-btn" onClick={() => setEditMode(true)}>
              Chỉnh sửa
            </button>
          )}
        </div>

        {/* ── Subscription badge ── */}
        {user?.subscription_plan && user.subscription_plan !== 'free' ? (
          <div className="subscription-banner subscription-banner--active">
            <span className="sub-badge sub-badge--paid">
              {user.subscription_plan === 'pro' ? '⭐ Pro' : '✦ Plus'}
            </span>
            <span className="sub-text">
              Gói {user.subscription_plan === 'pro' ? 'Pro' : 'Plus'} — hết hạn{' '}
              {user.subscription_expires_at
                ? new Date(user.subscription_expires_at).toLocaleDateString('vi-VN')
                : '—'}
            </span>
            <Link to="/bang-gia" className="sub-upgrade-link">Gia hạn</Link>
          </div>
        ) : (
          <div className="subscription-banner subscription-banner--free">
            <span className="sub-badge sub-badge--free">Miễn phí</span>
            <span className="sub-text">Nâng cấp để dùng không giới hạn</span>
            <Link to="/bang-gia" className="sub-upgrade-link sub-upgrade-link--cta">Nâng cấp ngay</Link>
          </div>
        )}

        {/* ── Stats ── */}
        <div className="stats-row">
          <StatCard icon="★" label="Điều luật đã lưu" value={stats.bookmarks} loading={statsLoading} />
          <StatCard icon="🕐" label="Lịch sử xem" value={stats.history} loading={statsLoading} />
          <StatCard icon="💬" label="Cuộc hội thoại" value={stats.conversations} loading={statsLoading} />
        </div>

        <div className="profile-sections">

          {/* ── Edit profile ── */}
          <section className="profile-section">
            <h2 className="section-title">Thông tin cá nhân</h2>
            {profileMsg && (
              <div className={`profile-msg ${profileMsg.type}`}>{profileMsg.text}</div>
            )}
            {editMode ? (
              <form className="profile-form" onSubmit={handleSaveProfile}>
                <div className="form-row">
                  <label>Họ và tên</label>
                  <input
                    type="text"
                    value={fullName}
                    onChange={e => setFullName(e.target.value)}
                    placeholder="Nhập họ và tên"
                  />
                </div>
                <div className="form-row">
                  <label>Email</label>
                  <input
                    type="email"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    placeholder="Nhập địa chỉ email"
                  />
                </div>
                <div className="form-row">
                  <label>Tên đăng nhập</label>
                  <input type="text" value={user?.username} disabled className="input-disabled" />
                </div>
                <div className="form-actions">
                  <button type="submit" className="btn-primary" disabled={profileSaving}>
                    {profileSaving ? 'Đang lưu...' : 'Lưu thay đổi'}
                  </button>
                  <button type="button" className="btn-ghost" onClick={handleCancelEdit}>
                    Hủy
                  </button>
                </div>
              </form>
            ) : (
              <div className="profile-info-list">
                <div className="info-row">
                  <span className="info-label">Họ và tên</span>
                  <span className="info-value">{user?.full_name || <em className="empty-val">Chưa cập nhật</em>}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Email</span>
                  <span className="info-value">{user?.email || <em className="empty-val">Chưa cập nhật</em>}</span>
                </div>
                <div className="info-row">
                  <span className="info-label">Tên đăng nhập</span>
                  <span className="info-value">{user?.username}</span>
                </div>
              </div>
            )}
          </section>

          {/* ── Change password ── */}
          <section className="profile-section">
            <h2 className="section-title">Đổi mật khẩu</h2>
            {pwMsg && (
              <div className={`profile-msg ${pwMsg.type}`}>{pwMsg.text}</div>
            )}
            <form className="profile-form" onSubmit={handleChangePassword}>
              <div className="form-row">
                <label>Mật khẩu hiện tại</label>
                <input
                  type="password"
                  value={currentPassword}
                  onChange={e => setCurrentPassword(e.target.value)}
                  required
                  placeholder="Nhập mật khẩu hiện tại"
                />
              </div>
              <div className="form-row">
                <label>Mật khẩu mới</label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={e => setNewPassword(e.target.value)}
                  required
                  placeholder="Ít nhất 6 ký tự"
                />
              </div>
              <div className="form-row">
                <label>Xác nhận mật khẩu mới</label>
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={e => setConfirmPassword(e.target.value)}
                  required
                  placeholder="Nhập lại mật khẩu mới"
                />
              </div>
              <div className="form-actions">
                <button type="submit" className="btn-primary" disabled={pwSaving}>
                  {pwSaving ? 'Đang xử lý...' : 'Đổi mật khẩu'}
                </button>
              </div>
            </form>
          </section>

          {/* ── Danger zone ── */}
          <section className="profile-section danger-zone">
            <h2 className="section-title">Tài khoản</h2>
            <div className="danger-row">
              <div>
                <p className="danger-label">Đăng xuất khỏi hệ thống</p>
                <p className="danger-desc">Phiên đăng nhập hiện tại sẽ kết thúc.</p>
              </div>
              <button
                className="btn-danger"
                onClick={() => { logout(); navigate('/') }}
              >
                Đăng xuất
              </button>
            </div>
          </section>

        </div>
      </div>
      <Footer />
    </div>
  )
}
