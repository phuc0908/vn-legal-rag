"""
Lộ trình pháp lý (tính năng Pro).

Nội dung chi tiết các bước được giữ ở server và CHỈ trả đầy đủ cho người dùng
gói Pro. Người chưa Pro / khách vãng lai chỉ nhận bản teaser (tiêu đề + tóm tắt,
bước đầu tiên xem được đầy đủ) — nội dung chi tiết & căn cứ pháp lý không bao giờ
gửi xuống trình duyệt nên không thể bị lộ qua DevTools.
"""
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from app.core.auth import get_current_user_optional

router = APIRouter(prefix="/roadmap", tags=["roadmap"])


# Số bước đầu cho xem miễn phí (làm teaser). Các bước còn lại yêu cầu Pro.
FREE_PREVIEW_STEPS = 1

# Thư mục chứa file mẫu (đặt file vào: backend/templates/<tên file>).
TEMPLATE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "templates")
DIVORCE_TEMPLATE_FILE = "mau-don-ly-hon.docx"

DIVORCE_ROADMAP = [
    {
        "icon": "🧭",
        "title": "Xác định loại ly hôn & điều kiện",
        "summary": "Có hai hình thức: thuận tình (cả hai đồng ý) và đơn phương (một bên yêu cầu). Việc xác định đúng hình thức quyết định hồ sơ và trình tự tiếp theo.",
        "points": [
            "Thuận tình: hai vợ chồng cùng tự nguyện, đã thỏa thuận về việc chia tài sản, trông nom, nuôi dưỡng, cấp dưỡng con.",
            "Đơn phương: một bên yêu cầu khi có căn cứ vợ/chồng có hành vi bạo lực gia đình hoặc vi phạm nghiêm trọng làm hôn nhân lâm vào tình trạng trầm trọng.",
            "Lưu ý: chồng không có quyền yêu cầu ly hôn khi vợ đang mang thai, sinh con hoặc nuôi con dưới 12 tháng tuổi.",
        ],
        "refs": ["Điều 51 Luật Hôn nhân và gia đình 2014", "Điều 55, 56 Luật Hôn nhân và gia đình 2014"],
        "ask": "Phân biệt ly hôn thuận tình và ly hôn đơn phương theo pháp luật Việt Nam? Điều kiện của mỗi hình thức là gì?",
    },
    {
        "icon": "📄",
        "title": "Chuẩn bị hồ sơ",
        "summary": "Hồ sơ đầy đủ giúp Tòa án thụ lý nhanh, tránh phải bổ sung nhiều lần.",
        "points": [
            "Đơn yêu cầu công nhận thuận tình ly hôn (thuận tình) hoặc Đơn khởi kiện ly hôn (đơn phương).",
            "Bản chính Giấy chứng nhận đăng ký kết hôn.",
            "Bản sao công chứng CCCD/CMND của vợ và chồng.",
            "Bản sao công chứng Giấy khai sinh của các con (nếu có con chung).",
            "Giấy tờ chứng minh tài sản chung, nợ chung (nếu yêu cầu Tòa chia tài sản).",
        ],
        "refs": ["Điều 189 Bộ luật Tố tụng dân sự 2015"],
        "ask": "Hồ sơ, giấy tờ cần chuẩn bị để nộp đơn ly hôn gồm những gì?",
    },
    {
        "icon": "🏛️",
        "title": "Nộp đơn tại Tòa án có thẩm quyền",
        "summary": "Nộp đúng Tòa án có thẩm quyền để tránh bị trả lại đơn.",
        "points": [
            "Ly hôn thuận tình: nộp tại Tòa án nhân dân cấp huyện nơi cư trú của một trong hai vợ chồng.",
            "Ly hôn đơn phương: nộp tại Tòa án nhân dân cấp huyện nơi bị đơn (người bị kiện) cư trú hoặc làm việc.",
            "Trường hợp có yếu tố nước ngoài: thuộc thẩm quyền Tòa án nhân dân cấp tỉnh.",
        ],
        "refs": ["Điều 35 Bộ luật Tố tụng dân sự 2015", "Điều 39 Bộ luật Tố tụng dân sự 2015"],
        "ask": "Nộp đơn ly hôn ở Tòa án nào? Cách xác định Tòa án có thẩm quyền giải quyết ly hôn?",
    },
    {
        "icon": "🤝",
        "title": "Hòa giải tại Tòa án",
        "summary": "Hòa giải là thủ tục bắt buộc trước khi đưa vụ án ra xét xử (trừ một số trường hợp không tiến hành hòa giải được).",
        "points": [
            "Nhà nước và xã hội khuyến khích hòa giải ở cơ sở trước khi ra Tòa.",
            "Sau khi thụ lý, Tòa án tiến hành hòa giải để vợ chồng đoàn tụ.",
            "Hòa giải thành: Tòa đình chỉ giải quyết. Hòa giải không thành: tiếp tục trình tự công nhận thuận tình hoặc xét xử.",
        ],
        "refs": ["Điều 54 Luật Hôn nhân và gia đình 2014", "Điều 205 Bộ luật Tố tụng dân sự 2015"],
        "ask": "Thủ tục hòa giải tại Tòa án trong vụ án ly hôn diễn ra như thế nào? Có bắt buộc không?",
    },
    {
        "icon": "⚖️",
        "title": "Tòa thụ lý và giải quyết",
        "summary": "Tùy hình thức ly hôn mà Tòa ra quyết định công nhận hoặc mở phiên tòa xét xử.",
        "points": [
            "Thuận tình: nếu xét thấy thỏa thuận tự nguyện và bảo đảm quyền lợi của vợ, con thì Tòa ra quyết định công nhận thuận tình ly hôn.",
            "Đơn phương: Tòa mở phiên tòa sơ thẩm; thời hạn chuẩn bị xét xử thường là 04 tháng, có thể gia hạn.",
            "Án phí ly hôn sơ thẩm thường ở mức 300.000đ (chưa tính tranh chấp tài sản).",
        ],
        "refs": ["Điều 55 Luật Hôn nhân và gia đình 2014", "Điều 203 Bộ luật Tố tụng dân sự 2015"],
        "ask": "Thời hạn giải quyết vụ án ly hôn là bao lâu và các bước Tòa án xử lý ra sao?",
    },
    {
        "icon": "👶",
        "title": "Quyền nuôi con & cấp dưỡng",
        "summary": "Tòa quyết định người trực tiếp nuôi con dựa trên quyền lợi mọi mặt của con.",
        "points": [
            "Con dưới 36 tháng tuổi được giao cho mẹ trực tiếp nuôi (trừ trường hợp khác).",
            "Con từ đủ 07 tuổi trở lên phải xem xét nguyện vọng của con.",
            "Người không trực tiếp nuôi con có nghĩa vụ cấp dưỡng cho con.",
        ],
        "refs": ["Điều 81 Luật Hôn nhân và gia đình 2014", "Điều 82, 116 Luật Hôn nhân và gia đình 2014"],
        "ask": "Sau ly hôn, quyền nuôi con được quyết định thế nào và nghĩa vụ cấp dưỡng ra sao?",
    },
    {
        "icon": "🏠",
        "title": "Chia tài sản chung",
        "summary": "Tài sản chung được chia theo thỏa thuận; nếu không thỏa thuận được thì Tòa chia.",
        "points": [
            "Nguyên tắc: chia đôi, nhưng có tính đến công sức đóng góp, hoàn cảnh của mỗi bên.",
            "Tài sản riêng của ai thuộc về người đó (trừ khi đã nhập vào tài sản chung).",
            "Bảo vệ quyền lợi chính đáng của vợ, con chưa thành niên.",
        ],
        "refs": ["Điều 59 Luật Hôn nhân và gia đình 2014"],
        "ask": "Nguyên tắc chia tài sản chung của vợ chồng khi ly hôn theo pháp luật Việt Nam?",
    },
    {
        "icon": "✅",
        "title": "Bản án/quyết định & thi hành",
        "summary": "Sau khi có bản án hoặc quyết định, các bên thực hiện theo phán quyết của Tòa.",
        "points": [
            "Đương sự có quyền kháng cáo bản án sơ thẩm trong thời hạn 15 ngày.",
            "Quyết định công nhận thuận tình ly hôn có hiệu lực pháp luật ngay, không bị kháng cáo theo thủ tục phúc thẩm.",
            "Trường hợp một bên không tự nguyện thi hành, bên kia có quyền yêu cầu cơ quan thi hành án dân sự.",
        ],
        "refs": ["Điều 273 Bộ luật Tố tụng dân sự 2015"],
        "ask": "Sau khi có bản án ly hôn, thủ tục kháng cáo và thi hành án được thực hiện thế nào?",
    },
]


def _is_pro(user: Optional[dict]) -> bool:
    """True nếu user là admin hoặc đang có gói Pro còn hạn."""
    if not user:
        return False
    if user.get("is_admin"):
        return True
    if user.get("subscription_plan") != "pro":
        return False
    expires = user.get("subscription_expires_at")
    if expires is None:
        return True
    if isinstance(expires, str):
        try:
            expires = datetime.fromisoformat(expires)
        except ValueError:
            return True
    return expires > datetime.now()


def _public_step(step: dict, unlocked: bool) -> dict:
    """Trả nội dung bước. Nếu bị khóa, chỉ kèm tiêu đề + tóm tắt (teaser),
    KHÔNG kèm chi tiết points/refs/ask."""
    if unlocked:
        return {**step, "locked": False}
    return {
        "icon": step["icon"],
        "title": step["title"],
        "summary": step["summary"],
        "locked": True,
    }


@router.get("/divorce")
async def get_divorce_roadmap(user: Optional[dict] = Depends(get_current_user_optional)):
    is_pro = _is_pro(user)
    steps = [
        _public_step(step, unlocked=is_pro or i < FREE_PREVIEW_STEPS)
        for i, step in enumerate(DIVORCE_ROADMAP)
    ]
    return {"is_pro": is_pro, "steps": steps}


@router.get("/divorce/template")
async def download_divorce_template(user: Optional[dict] = Depends(get_current_user_optional)):
    """Tải file mẫu đơn ly hôn (.docx). Chỉ dành cho gói Pro."""
    if not _is_pro(user):
        raise HTTPException(
            status_code=403,
            detail={"message": "Tính năng dành cho gói Pro", "required_plan": "pro"},
        )
    path = os.path.join(TEMPLATE_DIR, DIVORCE_TEMPLATE_FILE)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Chưa có file mẫu đơn trên hệ thống.")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename="Mau-don-ly-hon.docx",
    )
