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

        last_mine = user.get("last_automine_at")
        if last_mine:
            if last_mine.tzinfo is None:
                last_mine = last_mine.replace(tzinfo=timezone.utc)
            elapsed_hours = (datetime.now(timezone.utc) - last_mine).total_seconds() / 3600
            capped_hours = min(elapsed_hours, 24)
            if capped_hours > 0.01:
                c.execute("""
                    SELECT COALESCE(SUM(s.effect_value), 0) as rate
                    FROM inventory i JOIN shop_items s ON i.item_key = s.item_key
                    WHERE i.user_id = %s AND i.is_active = TRUE AND s.effect_type = 'auto_mine'
                        AND (i.expires_at IS NULL OR i.expires_at > NOW())
                """, (user_id,))
                rate_row = c.fetchone()
                rate = rate_row["rate"] if rate_row else 0
                if rate and rate > 0:
                    earned = round(rate * capped_hours, 6)
                    c.execute("""
                        UPDATE users SET balance_trx = balance_trx + %s, last_automine_at = NOW()
                        WHERE user_id = %s RETURNING *
                    """, (earned, user_id))
                    user = dict(c.fetchone())
                    c.execute("""
                        INSERT INTO transactions (user_id, type, currency, amount, metadata)
                        VALUES (%s, 'auto_mine', 'TRX', %s, %s)
                    """, (user_id, earned, json.dumps({"hours": round(capped_hours, 2), "rate": rate})))
                else:
                    c.execute("UPDATE users SET last_automine_at = NOW() WHERE user_id = %s", (user_id,))
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


def get_user_by_referral_code(code: str):
    with get_db_cursor() as c:
        c.execute("SELECT * FROM users WHERE referral_code = %s", (code,))
        row = c.fetchone()
        return dict(row) if row else None


def place_in_binary_tree(new_user_id: str, referrer_code: str) -> bool:
    from collections import deque
    referrer = get_user_by_referral_code(referrer_code)
    if not referrer or referrer["user_id"] == new_user_id:
        return False
    with get_db_cursor() as c:
        queue = deque([referrer["user_id"]])
        while queue:
            current_id = queue.popleft()
            c.execute("SELECT user_id, left_child, right_child, tree_depth FROM users WHERE user_id = %s", (current_id,))
            node = c.fetchone()
            if not node:
                continue
            if not node["left_child"]:
                c.execute("UPDATE users SET left_child = %s WHERE user_id = %s", (new_user_id, current_id))
                c.execute("UPDATE users SET parent_id = %s, tree_depth = %s WHERE user_id = %s",
                          (current_id, node["tree_depth"] + 1, new_user_id))
                return True
            if not node["right_child"]:
                c.execute("UPDATE users SET right_child = %s WHERE user_id = %s", (new_user_id, current_id))
                c.execute("UPDATE users SET parent_id = %s, tree_depth = %s WHERE user_id = %s",
                          (current_id, node["tree_depth"] + 1, new_user_id))
                return True
            queue.append(node["left_child"])
            queue.append(node["right_child"])
    return False


def check_binary_bonus(user_id: str):
    from datetime import datetime, timezone, timedelta
    with get_db_cursor() as c:
        c.execute("SELECT left_volume, right_volume, last_bonus_at FROM users WHERE user_id = %s", (user_id,))
        row = c.fetchone()
        if not row:
            return
        matched = min(row["left_volume"] or 0, row["right_volume"] or 0)
        if matched < config.BINARY_MATCH_VOLUME:
            return
        last_bonus = row["last_bonus_at"]
        if last_bonus:
            if last_bonus.tzinfo is None:
                last_bonus = last_bonus.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc) - last_bonus < timedelta(days=config.REFERRAL_BONUS_COOLDOWN_DAYS):
                return
        c.execute("""
            UPDATE users SET left_volume = left_volume - %s, right_volume = right_volume - %s,
                balance_trx = balance_trx + %s, cycle_count = cycle_count + 1, last_bonus_at = NOW()
            WHERE user_id = %s
        """, (config.BINARY_MATCH_VOLUME, config.BINARY_MATCH_VOLUME, config.REFERRAL_BONUS_AMOUNT, user_id))
        c.execute("""
            INSERT INTO transactions (user_id, type, currency, amount, metadata)
            VALUES (%s, 'binary_bonus', 'TRX', %s, %s)
        """, (user_id, config.REFERRAL_BONUS_AMOUNT, json.dumps({"matched_volume": config.BINARY_MATCH_VOLUME})))


def distribute_referral(user_id: str, currency: str, amount: float):
    balance_col = {"TRX": "balance_trx", "TON": "balance_ton", "USDT": "balance_usdt"}.get(currency)
    if not balance_col or amount <= 0:
        return
    with get_db_cursor() as c:
        c.execute("SELECT user_id, parent_id, left_child, right_child FROM users WHERE user_id = %s", (user_id,))
        current = c.fetchone()
        if not current:
            return
        level = 1
        while current and current["parent_id"] and level <= 20:
            c.execute("SELECT user_id, parent_id, left_child, right_child FROM users WHERE user_id = %s", (current["parent_id"],))
            parent = c.fetchone()
            if not parent:
                break
            if currency == "TRX":
                leg_col = "left_volume" if parent["left_child"] == current["user_id"] else "right_volume"
                c.execute(f"UPDATE users SET {leg_col} = {leg_col} + %s WHERE user_id = %s", (amount, parent["user_id"]))
            rate = config.REFERRAL_COMMISSION_RATES.get(level, 0)
            if rate > 0:
                commission = round(amount * (rate / 100), 6)
                c.execute(f"UPDATE users SET {balance_col} = {balance_col} + %s WHERE user_id = %s",
                          (commission, parent["user_id"]))
                c.execute("""
                    INSERT INTO referral_commissions (referrer_id, referred_id, level, amount, currency, is_paid, paid_at)
                    VALUES (%s, %s, %s, %s, %s, TRUE, NOW())
                """, (parent["user_id"], user_id, level, commission, currency))
                c.execute("""
                    INSERT INTO transactions (user_id, type, currency, amount, metadata)
                    VALUES (%s, 'referral_commission', %s, %s, %s)
                """, (parent["user_id"], currency, commission, json.dumps({"level": level, "from_user": user_id})))
            current = parent
            level += 1
    if currency == "TRX":
        node = user_id
        with get_db_cursor() as c:
            c.execute("SELECT parent_id FROM users WHERE user_id = %s", (node,))
            row = c.fetchone()
        ancestor = row["parent_id"] if row else None
        depth_guard = 0
        while ancestor and depth_guard < 20:
            check_binary_bonus(ancestor)
            with get_db_cursor() as c:
                c.execute("SELECT parent_id FROM users WHERE user_id = %s", (ancestor,))
                row = c.fetchone()
            ancestor = row["parent_id"] if row else None
            depth_guard += 1
