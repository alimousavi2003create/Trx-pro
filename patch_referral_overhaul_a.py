# 1) config.py - faster mining (10x reward, so ~10 taps per TRX at base mining_power)
with open("config.py", "r", encoding="utf-8") as f:
    content = f.read()
old_reward = "TAP_BASE_REWARD = 0.01"
new_reward = "TAP_BASE_REWARD = 0.1"
assert old_reward in content, "TAP_BASE_REWARD anchor not found"
content = content.replace(old_reward, new_reward, 1)
with open("config.py", "w", encoding="utf-8") as f:
    f.write(content)
print("config.py: tap reward increased 10x")

# 2) database.py - add left/right commission tracking columns
with open("database.py", "r", encoding="utf-8") as f:
    content = f.read()
anchor = '''        c.execute("""
            ALTER TABLE nfts ADD COLUMN IF NOT EXISTS mint_fee_currency TEXT
        """)'''
assert anchor in content, "nfts alter anchor not found in database.py"
new_alters = anchor + '''
        c.execute("""
            ALTER TABLE users ADD COLUMN IF NOT EXISTS left_commission_trx NUMERIC DEFAULT 0
        """)
        c.execute("""
            ALTER TABLE users ADD COLUMN IF NOT EXISTS right_commission_trx NUMERIC DEFAULT 0
        """)'''
content = content.replace(anchor, new_alters, 1)
with open("database.py", "w", encoding="utf-8") as f:
    f.write(content)
print("database.py: commission tracking columns added")

# 3) models.py - add pay_direct_referral_bonus and get_downline_count
with open("models.py", "r", encoding="utf-8") as f:
    content = f.read()

new_functions = '''

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
'''

content = content.rstrip() + "\n" + new_functions
with open("models.py", "w", encoding="utf-8") as f:
    f.write(content)
print("models.py: pay_direct_referral_bonus + get_downline_count added")
