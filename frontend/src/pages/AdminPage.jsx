import React, { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import Header from '../components/Header'
import Footer from '../components/Footer'
import { getAdminOverview, getAdminDaily, getAdminTopUsers, getAdminTopBookmarks, getAdminTopViewed } from '../services/api'
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

function MiniBar({ data, color }) {
  if (!data?.length) return <p className="no-data">Chưa có dữ liệu</p>
  const max = Math.max(...data.map(d => d.count), 1)
  return (
    <div className="mini-bar-chart">
      {data.map(d => (
        <div key={d.date} className="bar-col" title={`${d.date}: ${d.count}`}>
          <div className="bar-fill" style={{ height: `${(d.count / max) * 100}%`, background: color }} />
          <span className="bar-label">{d.date.slice(5)}</span>
        </div>
      ))}
    </div>
  )
}

// ── Main page ──────────────────────────────────────────────────────────────────

export default function AdminPage() {
  const { isAuthenticated, user } = useAuthStore()
  const navigate = useNavigate()

  const [overview, setOverview] = useState(null)
  const [daily, setDaily] = useState(null)
  const [topUsers, setTopUsers] = useState([])
  const [topBookmarks, setTopBookmarks] = useState([])
  const [topViewed, setTopViewed] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [activeTab, setActiveTab] = useState('overview')

  useEffect(() => {
    if (!isAuthenticated) { navigate('/login'); return }
    if (!user?.is_admin) { navigate('/'); return }

    setLoading(true)
    Promise.all([
      getAdminOverview(),
      getAdminDaily(),
      getAdminTopUsers(),
      getAdminTopBookmarks(),
      getAdminTopViewed(),
    ]).then(([ov, dy, tu, tb, tv]) => {
      setOverview(ov)
      setDaily(dy)
      setTopUsers(tu)
      setTopBookmarks(tb)
      setTopViewed(tv)
    }).catch(e => {
      setError(e.response?.data?.detail || 'Không thể tải dữ liệu admin')
    }).finally(() => setLoading(false))
  }, [isAuthenticated, user, navigate])

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

        {loading ? (
          <div className="admin-loading">Đang tải dữ liệu...</div>
        ) : (
          <>
            {/* ── Tabs ── */}
            <div className="admin-tabs">
              {[
                { key: 'overview', label: 'Tổng quan' },
                { key: 'activity', label: 'Hoạt động 30 ngày' },
                { key: 'users', label: 'Người dùng' },
                { key: 'content', label: 'Nội dung' },
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
            {activeTab === 'activity' && daily && (
              <div className="tab-content">
                <section className="admin-section">
                  <h2>Người dùng mới (30 ngày)</h2>
                  <MiniBar data={daily.new_users} color="var(--chart-blue)" />
                </section>
                <section className="admin-section">
                  <h2>Cuộc hội thoại mới (30 ngày)</h2>
                  <MiniBar data={daily.new_conversations} color="var(--chart-green)" />
                </section>
                <section className="admin-section">
                  <h2>Câu hỏi của người dùng (30 ngày)</h2>
                  <MiniBar data={daily.new_messages} color="var(--chart-red)" />
                </section>
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
                        </tr>
                      </thead>
                      <tbody>
                        {topUsers.map((u, i) => (
                          <tr key={u.id}>
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
