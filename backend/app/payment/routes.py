from fastapi import APIRouter, Depends, HTTPException, Request
from app.core.auth import get_current_user
from app.payment import service as svc
from app.payment.payos import create_payment_link, verify_webhook_signature
from app.payment.schemas import CreatePaymentResponse, TransactionOut
from typing import List

router = APIRouter(prefix="/subscription", tags=["subscription"])


@router.post("/create/{plan}", response_model=CreatePaymentResponse)
async def create_payment(plan: str, current_user=Depends(get_current_user)):
    if plan not in svc.PLANS:
        raise HTTPException(400, detail=f"Gói không hợp lệ. Chọn: {list(svc.PLANS.keys())}")

    plan_info  = svc.PLANS[plan]
    order_code = svc.create_pending_transaction(current_user["id"], plan)

    try:
        result = await create_payment_link(
            order_code=order_code,
            amount=plan_info["amount"],
            description=f"VN Legal {plan_info['name']}",
        )
    except Exception as e:
        raise HTTPException(502, detail=f"Không thể kết nối PayOS: {str(e)}")

    if result.get("code") != "00":
        raise HTTPException(502, detail=f"PayOS lỗi: {result.get('desc', 'unknown')}")

    return CreatePaymentResponse(
        checkout_url=result["data"]["checkoutUrl"],
        order_code=order_code,
        amount=plan_info["amount"],
        plan=plan,
    )


@router.post("/webhook")
async def payos_webhook(request: Request):
    """
    Endpoint nhận webhook từ PayOS sau khi thanh toán.
    PayOS tính signature trên body["data"], không phải toàn bộ body.
    """
    body = await request.json()
    print(f"[WEBHOOK] PayOS gọi: {body}")

    received_sig = body.get("signature", "")
    webhook_data = body.get("data", {})

    # Verify signature trên data object
    if not verify_webhook_signature(webhook_data, received_sig):
        print(f"[WEBHOOK] Signature không khớp. data={webhook_data}")
        raise HTTPException(400, detail="Chữ ký không hợp lệ")

    # Chỉ xử lý khi thanh toán thành công
    if body.get("code") != "00":
        order_code = str(webhook_data.get("orderCode", ""))
        if order_code:
            svc.cancel_transaction(order_code)
        return {"status": "ignored"}

    order_code = str(webhook_data.get("orderCode", ""))
    success = svc.confirm_payment(order_code)
    print(f"[WEBHOOK] order_code={order_code} success={success}")

    return {"status": "ok" if success else "already_processed"}


@router.get("/plans")
def get_plans():
    """Trả về thông tin các gói để frontend hiển thị."""
    return {
        plan_id: {
            "id":          plan_id,
            "name":        info["name"],
            "amount":      info["amount"],
            "days":        info["days"],
            "daily_limit": info["daily_limit"],
        }
        for plan_id, info in svc.PLANS.items()
    }


@router.get("/my-transactions", response_model=List[TransactionOut])
def my_transactions(current_user=Depends(get_current_user)):
    return svc.get_user_transactions(current_user["id"])


@router.get("/my-subscription")
def my_subscription(current_user=Depends(get_current_user)):
    info = svc.get_subscription_info(current_user["id"])
    return {
        "plan":       info["subscription_plan"] if info else "free",
        "expires_at": info["subscription_expires_at"] if info else None,
    }
