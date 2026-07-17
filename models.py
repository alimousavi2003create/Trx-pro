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


def create_nft(owner_id: str, name: str, image_data: str, mint_fee_amount: float = None, mint_fee_currency: str = None):
    with get_db_cursor() as c:
        c.execute("""
            INSERT INTO nfts (owner_id, creator_id, name, image_data, is_listed, mint_fee_amount, mint_fee_currency)
            VALUES (%s, %s, %s, %s, FALSE, %s, %s)
            RETURNING id, owner_id, creator_id, name, price, currency, is_listed, created_at
        """, (owner_id, owner_id, name, image_data, mint_fee_amount, mint_fee_currency))
        row = c.fetchone()
        return dict(row) if row else None


def delete_nft(nft_id: int, owner_id: str, refund_fee: bool = True):
    balance_cols = {"TRX": "balance_trx", "TON": "balance_ton", "USDT": "balance_usdt"}
    with get_db_cursor() as c:
        c.execute("SELECT * FROM nfts WHERE id = %s FOR UPDATE", (nft_id,))
        nft = c.fetchone()
        if not nft:
            return {"success": False, "error": "NFT not found"}
        if nft["owner_id"] != owner_id:
            return {"success": False, "error": "You do not own this NFT"}

        refunded_amount = None
        refunded_currency = None
        if refund_fee and nft["mint_fee_amount"] and nft["mint_fee_currency"]:
            balance_col = balance_cols.get(nft["mint_fee_currency"])
            if balance_col:
                c.execute(f"UPDATE users SET {balance_col} = {balance_col} + %s WHERE user_id = %s",
                          (nft["mint_fee_amount"], owner_id))
                c.execute("""
                    INSERT INTO transactions (user_id, type, currency, amount, metadata)
                    VALUES (%s, 'nft_delete_refund', %s, %s, %s)
                """, (owner_id, nft["mint_fee_currency"], nft["mint_fee_amount"], json.dumps({"nft_id": nft_id})))
                refunded_amount = float(nft["mint_fee_amount"])
                refunded_currency = nft["mint_fee_currency"]

        c.execute("DELETE FROM nfts WHERE id = %s", (nft_id,))
    return {"success": True, "refunded_amount": refunded_amount, "refunded_currency": refunded_currency}


def get_nft(nft_id: int):
    with get_db_cursor() as c:
        c.execute("SELECT * FROM nfts WHERE id = %s", (nft_id,))
        row = c.fetchone()
        return dict(row) if row else None


def get_user_nfts(user_id: str):
    with get_db_cursor() as c:
        c.execute("SELECT id, owner_id, creator_id, name, price, currency, is_listed, created_at FROM nfts WHERE owner_id = %s ORDER BY created_at DESC", (user_id,))
        return [dict(row) for row in c.fetchall()]


def get_marketplace_listings(limit: int = 50):
    with get_db_cursor() as c:
        c.execute("""
            SELECT id, owner_id, creator_id, name, price, currency, is_listed, created_at
            FROM nfts WHERE is_listed = TRUE ORDER BY updated_at DESC LIMIT %s
        """, (limit,))
        return [dict(row) for row in c.fetchall()]


def set_nft_listing(nft_id: int, owner_id: str, price: float, currency: str, is_listed: bool):
    with get_db_cursor() as c:
        c.execute("SELECT owner_id FROM nfts WHERE id = %s", (nft_id,))
        row = c.fetchone()
        if not row or row["owner_id"] != owner_id:
            return False
        c.execute("""
            UPDATE nfts SET price = %s, currency = %s, is_listed = %s, updated_at = NOW()
            WHERE id = %s
        """, (price, currency, is_listed, nft_id))
        return True


def transfer_nft(nft_id: int, buyer_id: str):
    """Atomically buy a listed NFT. Returns dict with success/error and financial breakdown."""
    balance_cols = {"TRX": "balance_trx", "TON": "balance_ton", "USDT": "balance_usdt"}
    with get_db_cursor() as c:
        c.execute("SELECT * FROM nfts WHERE id = %s FOR UPDATE", (nft_id,))
        nft = c.fetchone()
        if not nft:
            return {"success": False, "error": "NFT not found"}
        if not nft["is_listed"]:
            return {"success": False, "error": "NFT is not listed for sale"}
        if nft["owner_id"] == buyer_id:
            return {"success": False, "error": "Cannot buy your own NFT"}
        currency = nft["currency"]
        balance_col = balance_cols.get(currency)
        if not balance_col:
            return {"success": False, "error": "Invalid currency on listing"}
        price = float(nft["price"])
        buyer_pays = round(price * (1 + config.NFT_MARKETPLACE_BUYER_FEE_PERCENT / 100), 6)
        seller_gets = round(price * (1 - config.NFT_MARKETPLACE_SELLER_FEE_PERCENT / 100), 6)

        c.execute(f"SELECT {balance_col} as bal FROM users WHERE user_id = %s FOR UPDATE", (buyer_id,))
        buyer_row = c.fetchone()
        if not buyer_row or buyer_row["bal"] < buyer_pays:
            return {"success": False, "error": "Insufficient balance"}

        seller_id = nft["owner_id"]
        c.execute(f"UPDATE users SET {balance_col} = {balance_col} - %s WHERE user_id = %s", (buyer_pays, buyer_id))
        c.execute(f"UPDATE users SET {balance_col} = {balance_col} + %s WHERE user_id = %s", (seller_gets, seller_id))
        c.execute("""
            UPDATE nfts SET owner_id = %s, is_listed = FALSE, price = NULL, currency = NULL, updated_at = NOW()
            WHERE id = %s
        """, (buyer_id, nft_id))
        c.execute("""
            INSERT INTO transactions (user_id, type, currency, amount, metadata)
            VALUES (%s, 'nft_purchase', %s, %s, %s)
        """, (buyer_id, currency, -buyer_pays, json.dumps({"nft_id": nft_id, "seller_id": seller_id})))
        c.execute("""
            INSERT INTO transactions (user_id, type, currency, amount, metadata)
            VALUES (%s, 'nft_sale', %s, %s, %s)
        """, (seller_id, currency, seller_gets, json.dumps({"nft_id": nft_id, "buyer_id": buyer_id})))
    return {"success": True, "buyer_paid": buyer_pays, "seller_received": seller_gets, "currency": currency}


def get_nft(nft_id: int):
    with get_db_cursor() as c:
        c.execute("SELECT * FROM nfts WHERE id = %s", (nft_id,))
        row = c.fetchone()
        return dict(row) if row else None


def get_user_nfts(user_id: str):
    with get_db_cursor() as c:
        c.execute("SELECT id, owner_id, creator_id, name, price, currency, is_listed, created_at FROM nfts WHERE owner_id = %s ORDER BY created_at DESC", (user_id,))
        return [dict(row) for row in c.fetchall()]


def get_marketplace_listings(limit: int = 50):
    with get_db_cursor() as c:
        c.execute("""
            SELECT id, owner_id, creator_id, name, price, currency, is_listed, created_at
            FROM nfts WHERE is_listed = TRUE ORDER BY updated_at DESC LIMIT %s
        """, (limit,))
        return [dict(row) for row in c.fetchall()]


def set_nft_listing(nft_id: int, owner_id: str, price: float, currency: str, is_listed: bool):
    with get_db_cursor() as c:
        c.execute("SELECT owner_id FROM nfts WHERE id = %s", (nft_id,))
        row = c.fetchone()
        if not row or row["owner_id"] != owner_id:
            return False
        c.execute("""
            UPDATE nfts SET price = %s, currency = %s, is_listed = %s, updated_at = NOW()
            WHERE id = %s
        """, (price, currency, is_listed, nft_id))
        return True


def transfer_nft(nft_id: int, buyer_id: str):
    """Atomically buy a listed NFT. Returns dict with success/error and financial breakdown."""
    balance_cols = {"TRX": "balance_trx", "TON": "balance_ton", "USDT": "balance_usdt"}
    with get_db_cursor() as c:
        c.execute("SELECT * FROM nfts WHERE id = %s FOR UPDATE", (nft_id,))
        nft = c.fetchone()
        if not nft:
            return {"success": False, "error": "NFT not found"}
        if not nft["is_listed"]:
            return {"success": False, "error": "NFT is not listed for sale"}
        if nft["owner_id"] == buyer_id:
            return {"success": False, "error": "Cannot buy your own NFT"}
        currency = nft["currency"]
        balance_col = balance_cols.get(currency)
        if not balance_col:
            return {"success": False, "error": "Invalid currency on listing"}
        price = float(nft["price"])
        buyer_pays = round(price * (1 + config.NFT_MARKETPLACE_BUYER_FEE_PERCENT / 100), 6)
        seller_gets = round(price * (1 - config.NFT_MARKETPLACE_SELLER_FEE_PERCENT / 100), 6)

        c.execute(f"SELECT {balance_col} as bal FROM users WHERE user_id = %s FOR UPDATE", (buyer_id,))
        buyer_row = c.fetchone()
        if not buyer_row or buyer_row["bal"] < buyer_pays:
            return {"success": False, "error": "Insufficient balance"}

        seller_id = nft["owner_id"]
        c.execute(f"UPDATE users SET {balance_col} = {balance_col} - %s WHERE user_id = %s", (buyer_pays, buyer_id))
        c.execute(f"UPDATE users SET {balance_col} = {balance_col} + %s WHERE user_id = %s", (seller_gets, seller_id))
        c.execute("""
            UPDATE nfts SET owner_id = %s, is_listed = FALSE, price = NULL, currency = NULL, updated_at = NOW()
            WHERE id = %s
        """, (buyer_id, nft_id))
        c.execute("""
            INSERT INTO transactions (user_id, type, currency, amount, metadata)
            VALUES (%s, 'nft_purchase', %s, %s, %s)
        """, (buyer_id, currency, -buyer_pays, json.dumps({"nft_id": nft_id, "seller_id": seller_id})))
        c.execute("""
            INSERT INTO transactions (user_id, type, currency, amount, metadata)
            VALUES (%s, 'nft_sale', %s, %s, %s)
        """, (seller_id, currency, seller_gets, json.dumps({"nft_id": nft_id, "buyer_id": buyer_id})))
    return {"success": True, "buyer_paid": buyer_pays, "seller_received": seller_gets, "currency": currency}


def charge_nft_mint_fee(user_id: str, currency: str):
    fee_map = {"TRX": config.NFT_MINT_FEE_TRX, "TON": config.NFT_MINT_FEE_TON, "USDT": config.NFT_MINT_FEE_USDT}
    balance_cols = {"TRX": "balance_trx", "TON": "balance_ton", "USDT": "balance_usdt"}
    fee = fee_map.get(currency)
    balance_col = balance_cols.get(currency)
    if fee is None or not balance_col:
        return {"success": False, "error": "Invalid currency"}
    with get_db_cursor() as c:
        c.execute(f"SELECT {balance_col} as bal FROM users WHERE user_id = %s FOR UPDATE", (user_id,))
        row = c.fetchone()
        if not row or row["bal"] < fee:
            return {"success": False, "error": "Insufficient balance for mint fee"}
        c.execute(f"UPDATE users SET {balance_col} = {balance_col} - %s WHERE user_id = %s", (fee, user_id))
        c.execute("""
            INSERT INTO transactions (user_id, type, currency, amount, metadata)
            VALUES (%s, 'nft_mint_fee', %s, %s, %s)
        """, (user_id, currency, -fee, json.dumps({})))
    return {"success": True, "fee_charged": fee, "currency": currency}


def pay_direct_referral_bonus(user_id: str, currency: str, amount: float, source_type: str = "bonus"):
    balance_cols = {"TRX": "balance_trx", "TON": "balance_ton", "USDT": "balance_usdt"}
    balance_col = balance_cols.get(currency)
    if not balance_col or not amount or amount <= 0:
        return None
    bonus = round(amount * 0.10, 6)
    if bonus <= 0:
        return None
    with get_db_cursor() as c:
        c.execute("SELECT parent_id, left_child, right_child FROM users WHERE user_id = %s", (user_id,))
        row = c.fetchone()
        if not row or not row["parent_id"]:
            return None
        parent_id = row["parent_id"]
        c.execute("SELECT left_child, right_child FROM users WHERE user_id = %s", (parent_id,))
        parent = c.fetchone()
        if not parent:
            return None
        leg = "left" if parent["left_child"] == user_id else "right"

        c.execute(f"UPDATE users SET {balance_col} = {balance_col} + %s WHERE user_id = %s", (bonus, parent_id))
        if currency == "TRX":
            leg_col = "left_commission_trx" if leg == "left" else "right_commission_trx"
            c.execute(f"UPDATE users SET {leg_col} = {leg_col} + %s WHERE user_id = %s", (bonus, parent_id))
        c.execute("""
            INSERT INTO transactions (user_id, type, currency, amount, metadata)
            VALUES (%s, %s, %s, %s, %s)
        """, (parent_id, f"referral_{source_type}_bonus", currency, bonus, json.dumps({"from_user": user_id, "source_amount": amount})))
    return {"parent_id": parent_id, "bonus": bonus, "currency": currency, "leg": leg}


def get_downline_count_by_side(user_id: str):
    from collections import deque

    def count_subtree(root_id):
        if not root_id:
            return 0
        count = 0
        queue = deque([root_id])
        with get_db_cursor() as c:
            while queue:
                current_id = queue.popleft()
                count += 1
                c.execute("SELECT left_child, right_child FROM users WHERE user_id = %s", (current_id,))
                node = c.fetchone()
                if node:
                    if node["left_child"]:
                        queue.append(node["left_child"])
                    if node["right_child"]:
                        queue.append(node["right_child"])
        return count

    with get_db_cursor() as c:
        c.execute("SELECT left_child, right_child FROM users WHERE user_id = %s", (user_id,))
        row = c.fetchone()
        if not row:
            return 0, 0
    left_count = count_subtree(row["left_child"])
    right_count = count_subtree(row["right_child"])
    return left_count, right_count


def get_downline_count(user_id: str) -> int:
    from collections import deque
    count = 0
    with get_db_cursor() as c:
        c.execute("SELECT left_child, right_child FROM users WHERE user_id = %s", (user_id,))
        row = c.fetchone()
        if not row:
            return 0
        queue = deque()
        if row["left_child"]:
            queue.append(row["left_child"])
        if row["right_child"]:
            queue.append(row["right_child"])
        while queue:
            current_id = queue.popleft()
            count += 1
            c.execute("SELECT left_child, right_child FROM users WHERE user_id = %s", (current_id,))
            node = c.fetchone()
            if node:
                if node["left_child"]:
                    queue.append(node["left_child"])
                if node["right_child"]:
                    queue.append(node["right_child"])
    return count
