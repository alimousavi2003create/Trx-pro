"""TRX PRO - Telegram Authentication"""
import hashlib
import hmac
import json
from urllib.parse import parse_qsl
import config

def verify_init_data(init_data_raw: str) -> dict:
    if not init_data_raw:
        raise ValueError("initData is empty")
    parsed = dict(parse_qsl(init_data_raw))
    received_hash = parsed.pop("hash", "")
    if not received_hash:
        raise ValueError("hash field missing")
    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret_key = hmac.new(b"WebAppData", config.BOT_TOKEN.encode("utf-8"), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(computed_hash, received_hash):
        raise ValueError("initData signature verification failed")
    user_data = {}
    if "user" in parsed:
        try:
            user_data = json.loads(parsed["user"])
        except json.JSONDecodeError:
            pass
    return {
        "valid": True,
        "user_id": str(user_data.get("id", "")),
        "username": user_data.get("username", ""),
        "first_name": user_data.get("first_name", ""),
        "last_name": user_data.get("last_name", ""),
        "photo_url": user_data.get("photo_url", ""),
        "auth_date": parsed.get("auth_date", ""),
    }

def generate_referral_code(user_id: str) -> str:
    import random
    import string
    suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"TRX_{user_id[-6:]}_{suffix}"


def is_group_member(user_id: str) -> bool:
    import requests
    if not config.FORCE_JOIN_CHAT_ID:
        return True
    try:
        resp = requests.get(
            f"https://api.telegram.org/bot{config.BOT_TOKEN}/getChatMember",
            params={"chat_id": config.FORCE_JOIN_CHAT_ID, "user_id": user_id},
            timeout=10,
        )
        data = resp.json()
        if not data.get("ok"):
            return True
        status = data["result"]["status"]
        return status in ("member", "administrator", "creator")
    except Exception:
        return True
