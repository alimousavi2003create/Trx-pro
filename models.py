"""TRX PRO - Database Models"""
import json
from database import get_db_cursor
from auth import generate_referral_code
import config

def get_or_create_user(user_id: str, username: str = "", first_name: str = "",
                       last_name: str = "", photo_url: str = "") -> dict:
    with get_db_cursor() as c:
        c.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        user = c.fetchone()
        if not user:
            ref_code = generate_referral_code(user_id)
            c.execute("""
                INSERT INTO users (user_id, username, first_name, last_name, photo_url, referral_code)
                VALUES (%s, %s, %s, %s, %s, %s) RETURNING *
            """, (user_id, username, first_name, last_name, photo_url, ref_code))
            user = c.fetchone()
            c.execute("""
                INSERT INTO transactions (user_id, type, currency, amount, balance_after, metadata)
                VALUES (%s, 'signup', 'TRX', 0, 0, %s)
            """, (user_id, '{"source": "telegram"}'))
        return dict(user)

def get_user(user_id: str) -> dict:
    with get_db_cursor() as c:
        c.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
        row = c.fetchone()
        if not row:
            return None
        user = dict(row)
        from datetime import datetime, timezone
        last_refill = user.get("energy_last_refill")
        if last_refill and user["energy"] < user["energy_max"]:
            if last_refill.tzinfo is None:
                last_refill = last_refill.replace(tzinfo=timezone.utc)
            elapsed_seconds = (datetime.now(timezone.utc) - last_refill).total_seconds()
            regen_amount = int(elapsed_seconds // 60) * config.ENERGY_REGEN_RATE
            if regen_amount > 0:
                new_energy = min(user["energy_max"], user["energy"] + regen_amount)
                c.execute(
                    "UPDATE users SET energy = %s, energy_last_refill = NOW() WHERE user_id = %s RETURNING *",
                    (new_energy, user_id)
                )
                user = dict(c.fetchone())
        return user

def update_balance(user_id: str, currency: str, amount: float,
                   tx_type: str, metadata: dict = None) -> float:
    column = "balance_trx" if currency == "TRX" else "balance_ton"
    with get_db_cursor() as c:
        c.execute(f"SELECT {column} FROM users WHERE user_id = %s", (user_id,))
        row = c.fetchone()
        if not row:
            return None
        balance_before = row[column]
        balance_after = balance_before + amount
        if balance_after < 0:
            raise ValueError("Insufficient balance")
        c.execute(f"UPDATE users SET {column} = %s WHERE user_id = %s",
                  (balance_after, user_id))
        meta = metadata or {}
        c.execute("""
            INSERT INTO transactions (user_id, type, currency, amount, balance_before, balance_after, metadata)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (user_id, tx_type, currency, amount, balance_before, balance_after, json.dumps(meta)))
        return balance_after

def get_inventory(user_id: str) -> list:
    with get_db_cursor() as c:
        c.execute("""
            SELECT i.*, s.name, s.description, s.effect_type, s.effect_value,
                   s.icon_3d_url, s.rarity
            FROM inventory i JOIN shop_items s ON i.item_key = s.item_key
            WHERE i.user_id = %s AND i.is_active = TRUE ORDER BY s.sort_order
        """, (user_id,))
        return [dict(row) for row in c.fetchall()]

def get_transactions(user_id: str, limit: int = 50) -> list:
    with get_db_cursor() as c:
        c.execute("""
            SELECT * FROM transactions WHERE user_id = %s ORDER BY created_at DESC LIMIT %s
        """, (user_id, limit))
        return [dict(row) for row in c.fetchall()]
