"""
PayOS API client.
Docs: https://payos.vn/docs/api/
"""
import hmac
import hashlib
import httpx
from app.core.config import settings


PAYOS_BASE_URL = "https://api-merchant.payos.vn"


def _sign(data: dict) -> str:
    """
    Tạo chữ ký HMAC-SHA256 theo chuẩn PayOS.
    Chỉ sign các field được chỉ định, sort theo alphabet.
    """
    SIGN_FIELDS = {"amount", "cancelUrl", "description", "orderCode", "returnUrl"}
    payload = "&".join(
        f"{k}={data[k]}"
        for k in sorted(SIGN_FIELDS)
        if k in data
    )
    return hmac.new(
        settings.PAYOS_CHECKSUM_KEY.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()


def verify_webhook_signature(data: dict, received_sig: str) -> bool:
    """
    Xác minh chữ ký webhook từ PayOS.
    data là body["data"] (nested object), không phải toàn bộ body.
    PayOS tính signature từ: amount, code, desc, orderCode, status (sort alphabet).
    """
    WEBHOOK_SIGN_FIELDS = ["amount", "code", "desc", "orderCode", "status"]
    payload = "&".join(
        f"{k}={data.get(k, '')}"
        for k in WEBHOOK_SIGN_FIELDS  # đã sort sẵn theo alphabet
    )
    expected = hmac.new(
        settings.PAYOS_CHECKSUM_KEY.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()
    print(f"[WEBHOOK] payload_to_sign={payload!r}")
    print(f"[WEBHOOK] expected={expected}  received={received_sig}")
    return hmac.compare_digest(expected, received_sig)


async def create_payment_link(
    order_code: int,
    amount: int,
    description: str,
) -> dict:
    """
    Tạo link thanh toán PayOS.
    Trả về dict từ API PayOS, trong đó data.checkoutUrl là URL redirect user.
    """
    body = {
        "orderCode":   order_code,
        "amount":      amount,
        "description": description[:25],  # PayOS giới hạn 25 ký tự
        "returnUrl":   settings.PAYOS_RETURN_URL,
        "cancelUrl":   settings.PAYOS_CANCEL_URL,
    }
    body["signature"] = _sign(body)

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(
            f"{PAYOS_BASE_URL}/v2/payment-requests",
            json=body,
            headers={
                "x-client-id": settings.PAYOS_CLIENT_ID,
                "x-api-key":   settings.PAYOS_API_KEY,
            },
        )
    resp.raise_for_status()
    return resp.json()
