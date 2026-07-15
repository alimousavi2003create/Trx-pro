"""TRX PRO - Automatic TON Deposit Monitor"""
import time
import threading
import logging
import requests

import config
from database import get_db_cursor
from models import get_user

logger = logging.getLogger(__name__)

POLL_INTERVAL = 15


def _already_processed(tx_hash):
    with get_db_cursor() as c:
        c.execute("SELECT 1 FROM processed_deposits WHERE tx_hash = %s", (tx_hash,))
        return c.fetchone() is not None


def _mark_processed(tx_hash, user_id, currency, amount):
    with get_db_cursor() as c:
        c.execute("""
            INSERT INTO processed_deposits (tx_hash, user_id, currency, amount)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (tx_hash) DO NOTHING
        """, (tx_hash, user_id, currency, amount))


def _credit_user(user_id, currency, amount, tx_hash):
    balance_col = {"TRX": "balance_trx", "TON": "balance_ton", "USDT": "balance_usdt"}.get(currency, "balance_ton")
    with get_db_cursor() as c:
        c.execute(f"UPDATE users SET {balance_col} = {balance_col} + %s WHERE user_id = %s",
                   (amount, user_id))
        c.execute("""
            INSERT INTO transactions (user_id, type, currency, amount, metadata)
            VALUES (%s, 'deposit', %s, %s, %s)
        """, (user_id, currency, amount, '{"tx_hash": "' + tx_hash + '"}'))


def check_ton_deposits():
    if not config.PROJECT_WALLET_TON:
        return
    try:
        url = f"{config.TONCENTER_BASE}getTransactions"
        params = {"address": config.PROJECT_WALLET_TON, "limit": 20}
        if config.TONCENTER_API_KEY:
            params["api_key"] = config.TONCENTER_API_KEY
        resp = requests.get(url, params=params, timeout=10)
        data = resp.json()
        if not data.get("ok"):
            return
        for tx in data.get("result", []):
            in_msg = tx.get("in_msg", {})
            value = in_msg.get("value")
            comment = (in_msg.get("message") or "").strip()
            tx_hash = tx.get("transaction_id", {}).get("hash")
            if not value or not tx_hash or not comment:
                continue
            if int(value) <= 0:
                continue
            if _already_processed(tx_hash):
                continue
            user = get_user(comment)
            if not user:
                continue
            amount_ton = int(value) / 1e9
            _credit_user(comment, "TON", amount_ton, tx_hash)
            _mark_processed(tx_hash, comment, "TON", amount_ton)
            logger.info(f"Auto-credited {amount_ton} TON to user {comment} (tx {tx_hash})")
    except Exception as e:
        logger.error(f"TON deposit check failed: {e}")


def deposit_monitor_loop():
    while True:
        check_ton_deposits()
        time.sleep(POLL_INTERVAL)


def start_deposit_monitor():
    t = threading.Thread(target=deposit_monitor_loop, daemon=True)
    t.start()
    logger.info("TON deposit monitor started")
