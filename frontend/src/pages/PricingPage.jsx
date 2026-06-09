import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import Header from '../components/Header'
import Footer from '../components/Footer'
import { createPayment } from '../services/api'
import { useAuthStore } from '../store/authStore'
import '../styles/PricingPage.css'

const PLANS = [
  {
    id: 'plus',
    name: 'Plus',
    price: '99.000₫',
    period: '/tháng',
    color: 'blue',
    features: [
      '200 câu hỏi mỗi ngày',
      'Truy vấn pháp lý nâng cao',
      'Lưu không giới hạn',
      'Lịch sử hội thoại đầy đủ',
    ],
  },
  {
    id: 'pro',
    name: 'Pro',
    price: '199.000₫',
    period: '/tháng',
    color: 'gold',
    highlight: true,
    badge: 'Phổ biến nhất',
    features: [
      'Không giới hạn câu hỏi',
      'Ưu tiên xử lý',
      'Tất cả tính năng Plus',
      'Hỗ trợ ưu tiên',
    ],
  },
]

export default function PricingPage() {
  const { isAuthenticated } = useAuthStore()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(null)
  const [error, setError] = useState('')

  const handleBuy = async (planId) => {
    if (!isAuthenticated) {
      navigate('/login?redirect=/bang-gia')
      return
    }
    setLoading(planId)
    setError('')
    try {
      const { checkout_url } = await createPayment(planId)
      window.location.href = checkout_url
    } catch (e) {
      setError(e.response?.data?.detail || 'Không thể tạo đơn hàng. Vui lòng thử lại.')
    } finally {
      setLoading(null)
    }
  }

  return (
    <div className="pricing-page">
      <Header />
      <div className="pricing-body">
        <div className="pricing-header">
          <h1>Nâng cấp tài khoản</h1>
          <p>Trải nghiệm đầy đủ hệ thống tra cứu pháp luật Việt Nam</p>
        </div>

        {error && <div className="pricing-error">{error}</div>}

        <div className="pricing-grid">
          {/* Free */}
          <div className="plan-card plan-free">
            <div className="plan-name">Miễn phí</div>
            <div className="plan-price-wrap">
              <span className="plan-price">0₫</span>
              <span className="plan-period">/mãi mãi</span>
            </div>
            <ul className="plan-features">
              <li>20 câu hỏi mỗi ngày</li>
              <li>Tra cứu pháp điển cơ bản</li>
              <li>Lưu điều luật yêu thích</li>
            </ul>
            <button className="plan-btn plan-btn--current" disabled>
              Gói hiện tại
            </button>
          </div>

          {PLANS.map((plan) => (
            <div
              key={plan.id}
              className={`plan-card plan-${plan.color} ${plan.highlight ? 'plan-highlight' : ''}`}
            >
              {plan.badge && <div className="plan-badge">{plan.badge}</div>}
              <div className="plan-name">{plan.name}</div>
              <div className="plan-price-wrap">
                <span className="plan-price">{plan.price}</span>
                <span className="plan-period">{plan.period}</span>
              </div>
              <ul className="plan-features">
                {plan.features.map((f) => (
                  <li key={f}>{f}</li>
                ))}
              </ul>
              <button
                className={`plan-btn plan-btn--buy plan-btn--${plan.color}`}
                onClick={() => handleBuy(plan.id)}
                disabled={!!loading}
              >
                {loading === plan.id ? 'Đang xử lý...' : 'Mua ngay'}
              </button>
            </div>
          ))}
        </div>

        <p className="pricing-note">
          Thanh toán qua QR banking / chuyển khoản ngân hàng. Gói tự động gia hạn sau 30 ngày.
          Liên hệ hỗ trợ nếu có vấn đề.
        </p>
      </div>
      <Footer />
    </div>
  )
}
