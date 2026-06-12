"""
Business logic cho subscription & payment.
"""
import time
import random
from typing import Optional
from app.db.database import get_db, query_one, query_all


# Định nghĩa các gói
PLANS = {
    "plus": {
        "amount":        99_000,
        "name":          "Gói Plus",
        "days":          30,
        "daily_limit":   100,    # câu/ngày
    },
    "pro": {
        "amount":        199_000,
        "name":          "Gói Pro", 
        "days":          30,
        "daily_limit":   250,      # 0 = vô hạn
    },
}


def generate_order_code() -> int:
    """Sinh mã đơn hàng duy nhất (integer <= 9 chữ số, yêu cầu của PayOS)."""
    base = int(time.time()) % 100_000
    rand = random.randint(100, 999)
    return base * 1000 + rand


def create_pending_transaction(user_id: int, plan: str) -> int:
    """Tạo transaction trạng thái pending, trả về order_code."""
    order_code = generate_order_code()
    amount = PLANS[plan]["amount"]
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO transactions (user_id, order_code, plan, amount, status) "
                "VALUES (%s, %s, %s, %s, 'pending')",
                (user_id, str(order_code), plan, amount),
            )
            conn.commit()
    return order_code


def confirm_payment(order_code: str) -> bool:
    """
    Xác nhận thanh toán thành công (gọi từ webhook).
    Cập nhật transaction → paid, nâng cấp gói cho user.
    Idempotent: gọi nhiều lần cũng không bị duplicate.
    Trả về True nếu xử lý thành công, False nếu không tìm thấy hoặc đã xử lý.
    """
    tx = query_one(
        "SELECT * FROM transactions WHERE order_code = %s", (order_code,)
    )
    if not tx or tx["status"] == "paid":
        return False

    plan = tx["plan"]
    plan_info = PLANS.get(plan)
    if not plan_info:
        return False

    days        = plan_info["days"]
    daily_limit = plan_info["daily_limit"]

    with get_db() as conn:
        with conn.cursor() as cur:
            # Cập nhật transaction
            cur.execute(
                "UPDATE transactions SET status='paid', paid_at=NOW() WHERE order_code=%s",
                (order_code,),
            )
            # Nâng cấp user: cộng thêm ngày vào hạn hiện tại (nếu còn), hoặc tính từ now
            cur.execute(
                """UPDATE users SET
                       subscription_plan        = %s,
                       subscription_expires_at  = GREATEST(IFNULL(subscription_expires_at, NOW()), NOW())
                                                  + INTERVAL %s DAY,
                       daily_question_limit     = %s
                   WHERE id = %s""",
                (plan, days, daily_limit if daily_limit > 0 else None, tx["user_id"]),
            )
            conn.commit()
    return True


def cancel_transaction(order_code: str) -> None:
    """Đánh dấu đơn hàng bị huỷ."""
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE transactions SET status='cancelled' "
                "WHERE order_code=%s AND status='pending'",
                (order_code,),
            )
            conn.commit()


def get_user_transactions(user_id: int) -> list:
    return query_all(
        "SELECT id, order_code, plan, amount, status, created_at, paid_at "
        "FROM transactions WHERE user_id=%s ORDER BY created_at DESC LIMIT 20",
        (user_id,),
    )


def get_subscription_info(user_id: int) -> Optional[dict]:
    return query_one(
        "SELECT subscription_plan, subscription_expires_at FROM users WHERE id=%s",
        (user_id,),
    )
