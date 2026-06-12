import React, { useState, useEffect, useCallback } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import Header from '../components/Header'
import Footer from '../components/Footer'
import {
  getAdminOverview, getAdminDaily, getAdminTopUsers, getAdminTopBookmarks, getAdminTopViewed,
  getAdminAllUsers, getAdminSettings, updateGlobalDailyLimit, setUserDailyLimit, resetUserDailyLimit,
  toggleUserActive,
} from '../services/api'
import { useAuthStore } from '../store/authStore'
import '../styles/AdminPage.css'

// ── Helpers ────────────────────────────────────────────────────────────────────

function fmt(n) {
  if (n == null) return '—'
  return Number(n).toLocaleString('vi-VN')
}

function fmtDate(d) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('vi-VN')
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, color = 'default' }) {
  return (
    <div className={`stat-card-admin color-${color}`}>
      <span className="sca-value">{fmt(value)}</span>
      <span className="sca-label">{label}</span>
      {sub && <span className="sca-sub">{sub}</span>}
    </div>
  )
}

const RANGE_OPTIONS = [
  { days: 7,  label: '7 ngày' },
  { days: 30, label: '1 tháng' },
  { days: 90, label: '3 tháng' },
]

function MiniBar({ data, color }) {
  if (!data?.length) return <p className="no-data">Chưa có dữ liệu</p>
  const max = Math.max(...data.map(d => d.count), 1)
  const total = data.length
  const step = total <= 10 ? 1 : total <= 31 ? 5 : 14
  const yTicks = [max, Math.round(max / 2), 0]

  return (
    <div className="chart-wrapper">
      <div className="chart-y-axis">
        {yTicks.map((t, i) => (
          <span key={i} className="y-tick">{fmt(t)}</span>
        ))}
      </div>
      <div className="mini-bar-chart">
        {data.map((d, i) => (
          <div key={d.date} className="bar-col" title={`${d.date}: ${d.count}`}>
            <div className="bar-fill" style={{ height: `${(d.count / max) * 100}%`, background: color }} />
            <span className="bar-label" style={{ visibility: (i % step === 0 || i === total - 1) ? 'visible' : 'hidden' }}>
              {d.date.slice(5)}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Limits Tab ─────────────────────────────────────────────────────────────────

function LimitsTab() {
  const [globalLimit, setGlobalLimit] = useState(20)
  const [globalInput, setGlobalInput] = useState('20')
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [editingId, setEditingId] = useState(null)
  const [editValue, setEditValue] = useState('')

  const load = useCallback(() => {
    setLoading(true)
    Promise.all([getAdminSettings(), getAdminAllUsers()])
      .then(([settings, allUsers]) => {
        const lim = parseInt(settings.default_daily_limit) || 20
        setGlobalLimit(lim)
        setGlobalInput(String(lim))
        setUsers(allUsers)
      })
      .catch(() => setError('Không thể tải dữ liệu giới hạn'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => { load() }, [load])

  const flash = (msg, isError = false) => {
    if (isError) setError(msg)
    else setSuccess(msg)
    setTimeout(() => { setError(''); setSuccess('') }, 3000)
  }

  const handleSaveGlobal = async () => {
    const val = parseInt(globalInput)
    if (isNaN(val) || val < 0) { flash('Giá trị không hợp lệ (phải >= 0)', true); return }
    setSaving(true)
    try {
      await updateGlobalDailyLimit(val)
      setGlobalLimit(val)
      flash(`Đã cập nhật giới hạn mặc định: ${val === 0 ? 'Vô hạn' : `${val} câu/ngày`}`)
    } catch {
      flash('Không thể lưu cài đặt', true)
    } finally {
      setSaving(false)
    }
  }

  const startEdit = (u) => {
    setEditingId(u.id)
    setEditValue(u.daily_question_limit === null ? '' : String(u.daily_question_limit))
  }

  const cancelEdit = () => { setEditingId(null); setEditValue('') }

  const handleSaveUserLimit = async (userId) => {
    const raw = editValue.trim()
    const val = raw === '' ? null : parseInt(raw)
    if (raw !== '' && (isNaN(val) || val < 0)) { flash('Giá trị không hợp lệ (phải >= 0 hoặc để trống để dùng mặc định)', true); return }
    setSaving(true)
    try {
      if (raw === '') {
        await resetUserDailyLimit(userId)
      } else {
        await setUserDailyLimit(userId, val)
      }
      setUsers(prev => prev.map(u => u.id === userId ? { ...u, daily_question_limit: val } : u))
      cancelEdit()
      flash('Đã cập nhật giới hạn người dùng')
    } catch {
      flash('Không thể lưu giới hạn người dùng', true)
    } finally {
      setSaving(false)
    }
  }

  const handleReset = async (userId) => {
    setSaving(true)
    try {
      await resetUserDailyLimit(userId)
      setUsers(prev => prev.map(u => u.id === userId ? { ...u, daily_question_limit: null } : u))
      flash('Đã đặt lại về mặc định hệ thống')
    } catch {
      flash('Không thể đặt lại giới hạn', true)
    } finally {
      setSaving(false)
    }
  }

  const handleToggleBan = async (userId) => {
    setSaving(true)
    try {
      const result = await toggleUserActive(userId)
      setUsers(prev => prev.map(u => u.id === userId ? { ...u, is_active: result.is_active } : u))
      flash(result.is_active ? 'Đã mở khóa tài khoản' : 'Đã vô hiệu hóa tài khoản')
    } catch {
      flash('Không thể thay đổi trạng thái tài khoản', true)
    } finally {
      setSaving(false)
    }
  }

  const limitLabel = (u) => {
    if (u.is_admin) return <span className="limit-label-admin">Admin (vô hạn)</span>
    if (u.daily_question_limit === null) return <span className="limit-label-default">Mặc định ({globalLimit === 0 ? '∞' : globalLimit})</span>
    if (u.daily_question_limit === 0) return <span className="limit-label-unlimited">Vô hạn</span>
    return <span className="limit-label-custom">{u.daily_question_limit} câu/ngày</span>
  }

  if (loading) return <div className="admin-loading">Đang tải dữ liệu giới hạn...</div>

  return (
    <div className="tab-content">
      {error && <div className="admin-error">{error}</div>}
      {success && <div className="admin-success">{success}</div>}

      {/* Global settings */}
      <section className="admin-section">
        <h2>Giới hạn mặc định toàn hệ thống</h2>
        <div className="limit-global-row">
          <label className="limit-global-label">Số câu hỏi mỗi ngày (0 = vô hạn):</label>
          <div className="limit-global-inputs">
            <input
              type="number"
              min="0"
              className="limit-number-input"
              value={globalInput}
              onChange={e => setGlobalInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSaveGlobal()}
              disabled={saving}
            />
            <button className="limit-btn limit-btn--save" onClick={handleSaveGlobal} disabled={saving}>
              {saving ? 'Đang lưu...' : 'Lưu'}
            </button>
          </div>
          <p className="limit-global-hint">
            Áp dụng cho tất cả người dùng thường không có giới hạn riêng. Hiện tại: <strong>{globalLimit === 0 ? 'Vô hạn' : `${globalLimit} câu/ngày`}</strong>
          </p>
        </div>
      </section>

      {/* Per-user limits table */}
      <section className="admin-section">
        <h2>Giới hạn theo từng người dùng</h2>
        <div className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Username</th>
                <th>Họ tên</th>
                <th>Role</th>
                <th>Trạng thái</th>
                <th>Giới hạn/ngày</th>
                <th>Dùng hôm nay</th>
                <th>Thao tác</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u, i) => (
                <tr key={u.id} className={u.is_active == false ? 'row-banned' : ''}>
                  <td className="td-num">{i + 1}</td>
                  <td className="td-bold">{u.username}</td>
                  <td>{u.full_name || <em className="empty">—</em>}</td>
                  <td>
                    {u.is_admin
                      ? <span className="badge badge-admin">Admin</span>
                      : <span className="badge badge-user">User</span>
                    }
                  </td>
                  <td>
                    {u.is_admin
                      ? <em className="empty">—</em>
                      : u.is_active == false
                        ? <span className="badge badge-banned">Bị ban</span>
                        : <span className="badge badge-active">Hoạt động</span>
                    }
                  </td>
                  <td>
                    {editingId === u.id ? (
                      <input
                        type="number"
                        min="0"
                        className="limit-inline-input"
                        value={editValue}
                        onChange={e => setEditValue(e.target.value)}
                        onKeyDown={e => { if (e.key === 'Enter') handleSaveUserLimit(u.id); if (e.key === 'Escape') cancelEdit() }}
                        placeholder={`Mặc định (${globalLimit})`}
                        autoFocus
                      />
                    ) : (
                      limitLabel(u)
                    )}
                  </td>
                  <td className="td-num">
                    {u.is_admin ? <em className="empty">—</em> : (
                      <span className={u.today_question_count >= (u.daily_question_limit ?? globalLimit) && !u.is_admin && (u.daily_question_limit ?? globalLimit) > 0 ? 'quota-warn' : ''}>
                        {fmt(u.today_question_count)}
                      </span>
                    )}
                  </td>
                  <td>
                    {!u.is_admin && (
                      <div className="limit-actions">
                        {editingId === u.id ? (
                          <>
                            <button className="limit-btn limit-btn--save" onClick={() => handleSaveUserLimit(u.id)} disabled={saving}>Lưu</button>
                            <button className="limit-btn limit-btn--cancel" onClick={cancelEdit} disabled={saving}>Hủy</button>
                          </>
                        ) : (
                          <>
                            <button className="limit-btn limit-btn--edit" onClick={() => startEdit(u)} disabled={u.is_active == false}>Sửa</button>
                            {u.daily_question_limit !== null && (
                              <button className="limit-btn limit-btn--reset" onClick={() => handleReset(u.id)} disabled={saving || u.is_active == false}>Reset</button>
                            )}
                            <button
                              className={`limit-btn ${u.is_active == false ? 'limit-btn--unban' : 'limit-btn--ban'}`}
                              onClick={() => handleToggleBan(u.id)}
                              disabled={saving}
                            >
                              {u.is_active == false ? 'Mở khóa' : 'Ban'}
                            </button>
                          </>
                        )}
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}

// ── Main page ──────────────────────────────────────────────────────────────────

const VALID_TABS = ['overview', 'activity', 'users', 'content', 'limits']

export default function AdminPage() {
  const { isAuthenticated, user } = useAuthStore()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  const [overview, setOverview] = useState(null)
  const [topUsers, setTopUsers] = useState([])
  const [topBookmarks, setTopBookmarks] = useState([])
  const [topViewed, setTopViewed] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const rawTab = searchParams.get('tab')
  const activeTab = VALID_TABS.includes(rawTab) ? rawTab : 'overview'
  const setActiveTab = (tab) => setSearchParams({ tab }, { replace: true })

  const [activityDays, setActivityDays] = useState(30)
  const [activityData, setActivityData] = useState(null)
  const [activityLoading, setActivityLoading] = useState(false)

  useEffect(() => {
    if (!isAuthenticated) { navigate('/login'); return }
    if (!user?.is_admin) { navigate('/'); return }

    setLoading(true)
    Promise.all([
      getAdminOverview(),
      getAdminTopUsers(),
      getAdminTopBookmarks(),
      getAdminTopViewed(),
    ]).then(([ov, tu, tb, tv]) => {
      setOverview(ov)
      setTopUsers(tu)
      setTopBookmarks(tb)
      setTopViewed(tv)
    }).catch(e => {
      setError(e.response?.data?.detail || 'Không thể tải dữ liệu admin')
    }).finally(() => setLoading(false))
  }, [isAuthenticated, user, navigate])

  useEffect(() => {
    if (!isAuthenticated || !user?.is_admin) return
    setActivityLoading(true)
    getAdminDaily(activityDays)
      .then(setActivityData)
      .catch(() => {})
      .finally(() => setActivityLoading(false))
  }, [activityDays, isAuthenticated, user])

  if (!isAuthenticated || !user?.is_admin) return null

  return (
    <div className="admin-page">
      <Header />
      <div className="admin-body">

        <div className="admin-header">
          <h1>Bảng điều khiển Admin</h1>
          <p>Tổng quan hệ thống VN Legal RAG</p>
        </div>

        {error && <div className="admin-error">{error}</div>}

        {/* ── Tabs ── */}
        <div className="admin-tabs">
          {[
            { key: 'overview',  label: 'Tổng quan' },
            { key: 'activity',  label: 'Hoạt động' },
            { key: 'users',     label: 'Người dùng' },
            { key: 'content',   label: 'Nội dung' },
            { key: 'limits',    label: 'Giới hạn câu hỏi' },
          ].map(t => (
            <button
              key={t.key}
              className={`admin-tab-btn ${activeTab === t.key ? 'active' : ''}`}
              onClick={() => setActiveTab(t.key)}
            >
              {t.label}
            </button>
          ))}
        </div>

        {activeTab === 'limits' ? (
          <LimitsTab />
        ) : loading ? (
          <div className="admin-loading">Đang tải dữ liệu...</div>
        ) : (
          <>
            {/* ── OVERVIEW ── */}
            {activeTab === 'overview' && overview && (
              <div className="tab-content">

                <section className="admin-section">
                  <h2>Người dùng</h2>
                  <div className="stats-grid">
                    <StatCard label="Tổng người dùng" value={overview.users.total} color="blue" />
                    <StatCard label="Mới trong 7 ngày" value={overview.users.new_7d} color="green" />
                    <StatCard label="Mới trong 30 ngày" value={overview.users.new_30d} color="green" />
                    <StatCard label="Tài khoản admin" value={overview.users.admins} color="red" />
                  </div>
                </section>

                <section className="admin-section">
                  <h2>Cuộc hội thoại</h2>
                  <div className="stats-grid">
                    <StatCard label="Tổng (kể cả đã xóa)" value={overview.conversations.total} />
                    <StatCard label="Đang hoạt động" value={overview.conversations.active} color="green" />
                    <StatCard label="Đã xóa mềm" value={overview.conversations.deleted} color="red" />
                    <StatCard label="Hôm nay" value={overview.conversations.today} color="blue" />
                    <StatCard label="7 ngày qua" value={overview.conversations.this_week} color="blue" />
                    <StatCard label="TB / người dùng" value={overview.avg.convs_per_user} />
                  </div>
                </section>

                <section className="admin-section">
                  <h2>Tin nhắn</h2>
                  <div className="stats-grid">
                    <StatCard label="Tổng (kể cả đã xóa)" value={overview.messages.total} />
                    <StatCard label="Đang hoạt động" value={overview.messages.active} color="green" />
                    <StatCard label="Đã xóa mềm" value={overview.messages.deleted} color="red" />
                    <StatCard label="Từ người dùng" value={overview.messages.user_msgs} color="blue" />
                    <StatCard label="Từ AI" value={overview.messages.assistant_msgs} color="blue" />
                    <StatCard label="Hôm nay" value={overview.messages.today} color="green" />
                    <StatCard label="TB / cuộc trò chuyện" value={overview.avg.msgs_per_conversation} />
                  </div>
                </section>

                <section className="admin-section">
                  <h2>Pháp điển & Lưu trữ</h2>
                  <div className="stats-grid">
                    <StatCard label="Tổng bookmark" value={overview.bookmarks.total} color="blue" />
                    <StatCard label="Điều luật được bookmark" value={overview.bookmarks.unique_dieu} />
                    <StatCard label="Tổng lượt xem" value={overview.history.total} color="blue" />
                    <StatCard label="Điều luật đã xem" value={overview.history.unique_dieu} />
                    <StatCard label="Người dùng đã xem" value={overview.history.unique_users} />
                  </div>
                </section>

              </div>
            )}

            {/* ── ACTIVITY ── */}
            {activeTab === 'activity' && (
              <div className="tab-content">
                <div className="activity-range-btns">
                  {RANGE_OPTIONS.map(opt => (
                    <button
                      key={opt.days}
                      className={`range-btn ${activityDays === opt.days ? 'active' : ''}`}
                      onClick={() => setActivityDays(opt.days)}
                    >
                      {opt.label}
                    </button>
                  ))}
                </div>
                {activityLoading ? (
                  <div className="admin-loading">Đang tải...</div>
                ) : activityData ? (
                  <>
                    <section className="admin-section">
                      <h2>Người dùng mới ({RANGE_OPTIONS.find(o => o.days === activityDays)?.label})</h2>
                      <MiniBar data={activityData.new_users} color="var(--chart-blue)" />
                    </section>
                    <section className="admin-section">
                      <h2>Cuộc hội thoại mới ({RANGE_OPTIONS.find(o => o.days === activityDays)?.label})</h2>
                      <MiniBar data={activityData.new_conversations} color="var(--chart-green)" />
                    </section>
                    <section className="admin-section">
                      <h2>Câu hỏi của người dùng ({RANGE_OPTIONS.find(o => o.days === activityDays)?.label})</h2>
                      <MiniBar data={activityData.new_messages} color="var(--chart-red)" />
                    </section>
                  </>
                ) : null}
              </div>
            )}

            {/* ── USERS ── */}
            {activeTab === 'users' && (
              <div className="tab-content">
                <section className="admin-section">
                  <h2>Người dùng hoạt động nhiều nhất</h2>
                  <div className="admin-table-wrap">
                    <table className="admin-table">
                      <thead>
                        <tr>
                          <th>#</th>
                          <th>Username</th>
                          <th>Họ tên</th>
                          <th>Email</th>
                          <th>Hội thoại</th>
                          <th>Tin nhắn</th>
                          <th>Bookmark</th>
                          <th>Ngày tạo</th>
                          <th>Role</th>
                          <th>Trạng thái</th>
                        </tr>
                      </thead>
                      <tbody>
                        {topUsers.map((u, i) => (
                          <tr key={u.id} className={u.is_active == false ? 'row-banned' : ''}>
                            <td className="td-num">{i + 1}</td>
                            <td className="td-bold">{u.username}</td>
                            <td>{u.full_name || <em className="empty">—</em>}</td>
                            <td>{u.email || <em className="empty">—</em>}</td>
                            <td className="td-num">{fmt(u.conversation_count)}</td>
                            <td className="td-num">{fmt(u.message_count)}</td>
                            <td className="td-num">{fmt(u.bookmark_count)}</td>
                            <td>{fmtDate(u.created_at)}</td>
                            <td>
                              {u.is_admin
                                ? <span className="badge badge-admin">Admin</span>
                                : <span className="badge badge-user">User</span>
                              }
                            </td>
                            <td>
                              {u.is_active == false
                                ? <span className="badge badge-banned">Bị ban</span>
                                : <span className="badge badge-active">Hoạt động</span>
                              }
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              </div>
            )}

            {/* ── CONTENT ── */}
            {activeTab === 'content' && (
              <div className="tab-content">
                <section className="admin-section">
                  <h2>Điều luật được bookmark nhiều nhất</h2>
                  <div className="admin-table-wrap">
                    <table className="admin-table">
                      <thead>
                        <tr><th>#</th><th>Điều luật</th><th>Chủ đề</th><th>Lượt lưu</th></tr>
                      </thead>
                      <tbody>
                        {topBookmarks.map((b, i) => (
                          <tr key={b.mapc}>
                            <td className="td-num">{i + 1}</td>
                            <td>
                              <Link to={`/phap-dien/dieu/${encodeURIComponent(b.mapc)}`} className="table-link">
                                {b.ten || b.mapc}
                              </Link>
                            </td>
                            <td>{b.chude_ten || '—'}</td>
                            <td className="td-num td-bold">{fmt(b.count)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>

                <section className="admin-section">
                  <h2>Điều luật được xem nhiều nhất</h2>
                  <div className="admin-table-wrap">
                    <table className="admin-table">
                      <thead>
                        <tr><th>#</th><th>Điều luật</th><th>Chủ đề</th><th>Lượt xem</th></tr>
                      </thead>
                      <tbody>
                        {topViewed.map((v, i) => (
                          <tr key={v.mapc}>
                            <td className="td-num">{i + 1}</td>
                            <td>
                              <Link to={`/phap-dien/dieu/${encodeURIComponent(v.mapc)}`} className="table-link">
                                {v.ten || v.mapc}
                              </Link>
                            </td>
                            <td>{v.chude_ten || '—'}</td>
                            <td className="td-num td-bold">{fmt(v.count)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </section>
              </div>
            )}
          </>
        )}
      </div>
      <Footer />
    </div>
  )
}
