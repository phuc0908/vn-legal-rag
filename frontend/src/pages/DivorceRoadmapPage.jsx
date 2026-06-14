import React from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Header from '../components/Header'
import Footer from '../components/Footer'
import { useAuthStore } from '../store/authStore'
import '../styles/DivorceRoadmapPage.css'

// ── Nội dung lộ trình pháp lý ly hôn ─────────────────────────────────────────
// Mỗi bước có phần giải thích tĩnh + trích dẫn căn cứ pháp lý. Nút "Hỏi sâu"
// điều hướng sang trợ lý AI với module Hôn nhân & Gia đình được bật sẵn.
const STEPS = [
  {
    icon: '🧭',
    title: 'Xác định loại ly hôn & điều kiện',
    summary:
      'Có hai hình thức: thuận tình (cả hai đồng ý) và đơn phương (một bên yêu cầu). Việc xác định đúng hình thức quyết định hồ sơ và trình tự tiếp theo.',
    points: [
      'Thuận tình: hai vợ chồng cùng tự nguyện, đã thỏa thuận về việc chia tài sản, trông nom, nuôi dưỡng, cấp dưỡng con.',
      'Đơn phương: một bên yêu cầu khi có căn cứ vợ/chồng có hành vi bạo lực gia đình hoặc vi phạm nghiêm trọng làm hôn nhân lâm vào tình trạng trầm trọng.',
      'Lưu ý: chồng không có quyền yêu cầu ly hôn khi vợ đang mang thai, sinh con hoặc nuôi con dưới 12 tháng tuổi.',
    ],
    refs: ['Điều 51 Luật Hôn nhân và gia đình 2014', 'Điều 55, 56 Luật Hôn nhân và gia đình 2014'],
    ask: 'Phân biệt ly hôn thuận tình và ly hôn đơn phương theo pháp luật Việt Nam? Điều kiện của mỗi hình thức là gì?',
  },
  {
    icon: '📄',
    title: 'Chuẩn bị hồ sơ',
    summary:
      'Hồ sơ đầy đủ giúp Tòa án thụ lý nhanh, tránh phải bổ sung nhiều lần.',
    points: [
      'Đơn yêu cầu công nhận thuận tình ly hôn (thuận tình) hoặc Đơn khởi kiện ly hôn (đơn phương).',
      'Bản chính Giấy chứng nhận đăng ký kết hôn.',
      'Bản sao công chứng CCCD/CMND của vợ và chồng.',
      'Bản sao công chứng Giấy khai sinh của các con (nếu có con chung).',
      'Giấy tờ chứng minh tài sản chung, nợ chung (nếu yêu cầu Tòa chia tài sản).',
    ],
    refs: ['Điều 189 Bộ luật Tố tụng dân sự 2015'],
    ask: 'Hồ sơ, giấy tờ cần chuẩn bị để nộp đơn ly hôn gồm những gì?',
  },
  {
    icon: '🏛️',
    title: 'Nộp đơn tại Tòa án có thẩm quyền',
    summary:
      'Nộp đúng Tòa án có thẩm quyền để tránh bị trả lại đơn.',
    points: [
      'Ly hôn thuận tình: nộp tại Tòa án nhân dân cấp huyện nơi cư trú của một trong hai vợ chồng.',
      'Ly hôn đơn phương: nộp tại Tòa án nhân dân cấp huyện nơi bị đơn (người bị kiện) cư trú hoặc làm việc.',
      'Trường hợp có yếu tố nước ngoài: thuộc thẩm quyền Tòa án nhân dân cấp tỉnh.',
    ],
    refs: ['Điều 35 Bộ luật Tố tụng dân sự 2015', 'Điều 39 Bộ luật Tố tụng dân sự 2015'],
    ask: 'Nộp đơn ly hôn ở Tòa án nào? Cách xác định Tòa án có thẩm quyền giải quyết ly hôn?',
  },
  {
    icon: '🤝',
    title: 'Hòa giải tại Tòa án',
    summary:
      'Hòa giải là thủ tục bắt buộc trước khi đưa vụ án ra xét xử (trừ một số trường hợp không tiến hành hòa giải được).',
    points: [
      'Nhà nước và xã hội khuyến khích hòa giải ở cơ sở trước khi ra Tòa.',
      'Sau khi thụ lý, Tòa án tiến hành hòa giải để vợ chồng đoàn tụ.',
      'Hòa giải thành: Tòa đình chỉ giải quyết. Hòa giải không thành: tiếp tục trình tự công nhận thuận tình hoặc xét xử.',
    ],
    refs: ['Điều 54 Luật Hôn nhân và gia đình 2014', 'Điều 205 Bộ luật Tố tụng dân sự 2015'],
    ask: 'Thủ tục hòa giải tại Tòa án trong vụ án ly hôn diễn ra như thế nào? Có bắt buộc không?',
  },
  {
    icon: '⚖️',
    title: 'Tòa thụ lý và giải quyết',
    summary:
      'Tùy hình thức ly hôn mà Tòa ra quyết định công nhận hoặc mở phiên tòa xét xử.',
    points: [
      'Thuận tình: nếu xét thấy thỏa thuận tự nguyện và bảo đảm quyền lợi của vợ, con thì Tòa ra quyết định công nhận thuận tình ly hôn.',
      'Đơn phương: Tòa mở phiên tòa sơ thẩm; thời hạn chuẩn bị xét xử thường là 04 tháng, có thể gia hạn.',
      'Án phí ly hôn sơ thẩm thường ở mức 300.000đ (chưa tính tranh chấp tài sản).',
    ],
    refs: ['Điều 55 Luật Hôn nhân và gia đình 2014', 'Điều 203 Bộ luật Tố tụng dân sự 2015'],
    ask: 'Thời hạn giải quyết vụ án ly hôn là bao lâu và các bước Tòa án xử lý ra sao?',
  },
  {
    icon: '👶',
    title: 'Quyền nuôi con & cấp dưỡng',
    summary:
      'Tòa quyết định người trực tiếp nuôi con dựa trên quyền lợi mọi mặt của con.',
    points: [
      'Con dưới 36 tháng tuổi được giao cho mẹ trực tiếp nuôi (trừ trường hợp khác).',
      'Con từ đủ 07 tuổi trở lên phải xem xét nguyện vọng của con.',
      'Người không trực tiếp nuôi con có nghĩa vụ cấp dưỡng cho con.',
    ],
    refs: ['Điều 81 Luật Hôn nhân và gia đình 2014', 'Điều 82, 116 Luật Hôn nhân và gia đình 2014'],
    ask: 'Sau ly hôn, quyền nuôi con được quyết định thế nào và nghĩa vụ cấp dưỡng ra sao?',
  },
  {
    icon: '🏠',
    title: 'Chia tài sản chung',
    summary:
      'Tài sản chung được chia theo thỏa thuận; nếu không thỏa thuận được thì Tòa chia.',
    points: [
      'Nguyên tắc: chia đôi, nhưng có tính đến công sức đóng góp, hoàn cảnh của mỗi bên.',
      'Tài sản riêng của ai thuộc về người đó (trừ khi đã nhập vào tài sản chung).',
      'Bảo vệ quyền lợi chính đáng của vợ, con chưa thành niên.',
    ],
    refs: ['Điều 59 Luật Hôn nhân và gia đình 2014'],
    ask: 'Nguyên tắc chia tài sản chung của vợ chồng khi ly hôn theo pháp luật Việt Nam?',
  },
  {
    icon: '✅',
    title: 'Bản án/quyết định & thi hành',
    summary:
      'Sau khi có bản án hoặc quyết định, các bên thực hiện theo phán quyết của Tòa.',
    points: [
      'Đương sự có quyền kháng cáo bản án sơ thẩm trong thời hạn 15 ngày.',
      'Quyết định công nhận thuận tình ly hôn có hiệu lực pháp luật ngay, không bị kháng cáo theo thủ tục phúc thẩm.',
      'Trường hợp một bên không tự nguyện thi hành, bên kia có quyền yêu cầu cơ quan thi hành án dân sự.',
    ],
    refs: ['Điều 273 Bộ luật Tố tụng dân sự 2015'],
    ask: 'Sau khi có bản án ly hôn, thủ tục kháng cáo và thi hành án được thực hiện thế nào?',
  },
]

function isProUser(user) {
  if (!user) return false
  if (user.is_admin) return true
  if (user.subscription_plan !== 'pro') return false
  // Kiểm tra hạn sử dụng nếu có
  if (user.subscription_expires_at) {
    return new Date(user.subscription_expires_at) > new Date()
  }
  return true
}

export default function DivorceRoadmapPage() {
  const { user } = useAuthStore()
  const navigate = useNavigate()
  const isPro = isProUser(user)

  const handleAsk = (question) => {
    if (!isPro) {
      navigate('/bang-gia')
      return
    }
    navigate(`/tu-van?q=${encodeURIComponent(question)}&module=hon_nhan`)
  }

  return (
    <div className="roadmap-page">
      <Header />
      <div className="roadmap-body">
        <div className="roadmap-hero">
          <span className="roadmap-pro-badge">⭐ Tính năng Pro</span>
          <h1>Lộ trình pháp lý về ly hôn</h1>
          <p>
            Hướng dẫn từng bước thủ tục ly hôn theo pháp luật Việt Nam — từ xác định
            hình thức, chuẩn bị hồ sơ, đến chia tài sản và quyền nuôi con. Mỗi bước
            kèm căn cứ pháp lý và có thể hỏi sâu với trợ lý AI.
          </p>
          <p className="roadmap-disclaimer">
            ⚠️ Nội dung mang tính tham khảo, không thay thế tư vấn của luật sư trong từng vụ việc cụ thể.
          </p>
        </div>

        {!isPro && (
          <div className="roadmap-cta-banner">
            <div className="roadmap-cta-text">
              <strong>Mở khóa toàn bộ lộ trình với gói Pro</strong>
              <span>Xem chi tiết tất cả các bước và hỏi sâu không giới hạn với trợ lý AI.</span>
            </div>
            <Link to="/bang-gia" className="roadmap-cta-btn">Nâng cấp Pro →</Link>
          </div>
        )}

        <div className="roadmap-timeline">
          {STEPS.map((step, index) => {
            // Người chưa Pro: bước đầu hiển thị đầy đủ làm teaser, các bước sau bị khóa.
            const locked = !isPro && index >= 1
            return (
              <div
                key={index}
                className={`roadmap-step${locked ? ' roadmap-step--locked' : ''}`}
              >
                <div className="roadmap-step-marker">
                  <span className="roadmap-step-num">{index + 1}</span>
                </div>
                <div className="roadmap-step-card">
                  <div className="roadmap-step-head">
                    <h2 className="roadmap-step-title">{step.title}</h2>
                  </div>
                  <p className="roadmap-step-summary">{step.summary}</p>

                  {locked ? (
                    <div className="roadmap-lock-overlay">
                      <span className="roadmap-lock-icon">🔒</span>
                      <span>Nâng cấp gói Pro để xem chi tiết bước này</span>
                      <Link to="/bang-gia" className="roadmap-lock-btn">Mở khóa</Link>
                    </div>
                  ) : (
                    <>
                      <ul className="roadmap-step-points">
                        {step.points.map((p, i) => (
                          <li key={i}>{p}</li>
                        ))}
                      </ul>
                      <div className="roadmap-step-refs">
                        <span className="roadmap-refs-label">Căn cứ pháp lý:</span>
                        {step.refs.map((r, i) => (
                          <span key={i} className="roadmap-ref-chip">{r}</span>
                        ))}
                      </div>
                      <button
                        className="roadmap-ask-btn"
                        onClick={() => handleAsk(step.ask)}
                      >
                        💬 Hỏi sâu với trợ lý AI
                      </button>
                    </>
                  )}
                </div>
              </div>
            )
          })}
        </div>

        {!isPro && (
          <div className="roadmap-footer-cta">
            <h3>Sẵn sàng đi hết lộ trình?</h3>
            <p>Nâng cấp lên gói Pro để mở khóa toàn bộ hướng dẫn chi tiết và hỏi đáp chuyên sâu.</p>
            <Link to="/bang-gia" className="roadmap-cta-btn">Xem các gói cước</Link>
          </div>
        )}
      </div>
      <Footer />
    </div>
  )
}
