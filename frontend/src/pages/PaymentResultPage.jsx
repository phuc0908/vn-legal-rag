import React, { useEffect, useState } from 'react'
import { useSearchParams, Link } from 'react-router-dom'
import Header from '../components/Header'
import Footer from '../components/Footer'
import { getMe } from '../services/api'
import { useAuthStore } from '../store/authStore'
import '../styles/PaymentResultPage.css'

export default function PaymentResultPage() {
  const [searchParams] = useSearchParams()
  const { updateUser } = useAuthStore()
  const [refreshed, setRefreshed] = useState(false)

  // PayOS trả về ?status=PAID | CANCELLED | ERROR và ?orderCode=xxx
  const status    = searchParams.get('status')   // "PAID" | "CANCELLED"
  const orderCode = searchParams.get('orderCode')
  const isPaid    = status === 'PAID'

  // Sau khi thanh toán thành công, cập nhật lại user trong store
  useEffect(() => {
    if (!isPaid) return
    getMe()
      .then((fresh) => { updateUser(fresh); setRefreshed(true) })
      .catch(() => setRefreshed(true))
  }, [isPaid, updateUser])

  return (
    <div className="result-page">
      <Header />
      <div className="result-body">
        {isPaid ? (
          <div className="result-card result-success">
            <div className="result-icon">✓</div>
            <h1>Thanh toán thành công!</h1>
            <p>Gói của bạn đã được kích hoạt. Mã đơn: <strong>{orderCode}</strong></p>
            <div className="result-actions">
              <Link to="/tu-van" className="result-btn result-btn--primary">
                Bắt đầu tư vấn
              </Link>
              <Link to="/ho-so" className="result-btn result-btn--secondary">
                Xem hồ sơ
              </Link>
            </div>
          </div>
        ) : (
          <div className="result-card result-fail">
            <div className="result-icon">✕</div>
            <h1>Thanh toán chưa hoàn tất</h1>
            <p>Đơn hàng đã bị huỷ hoặc xảy ra lỗi. Bạn chưa bị trừ tiền.</p>
            <div className="result-actions">
              <Link to="/bang-gia" className="result-btn result-btn--primary">
                Thử lại
              </Link>
              <Link to="/" className="result-btn result-btn--secondary">
                Về trang chủ
              </Link>
            </div>
          </div>
        )}
      </div>
      <Footer />
    </div>
  )
}
