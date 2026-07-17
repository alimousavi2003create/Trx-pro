with open("models.py", "r", encoding="utf-8") as f:
    content = f.read()

# Remove duplicate old create_nft (3-arg version)
old_create_nft = '''def create_nft(owner_id: str, name: str, image_data: str):
    with get_db_cursor() as c:
        c.execute("""
            INSERT INTO nfts (owner_id, creator_id, name, image_data, is_listed)
            VALUES (%s, %s, %s, %s, FALSE)
            RETURNING id, owner_id, creator_id, name, price, currency, is_listed, created_at
        """, (owner_id, owner_id, name, image_data))
        row = c.fetchone()
        return dict(row) if row else None


'''
assert old_create_nft in content, "duplicate create_nft anchor not found"
content = content.replace(old_create_nft, "", 1)

# Remove duplicate charge_nft_mint_fee (second occurrence)
old_charge_fee = '''def charge_nft_mint_fee(user_id: str, currency: str):
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


'''
count_occurrences = content.count(old_charge_fee)
print(f"charge_nft_mint_fee duplicate block found {count_occurrences} time(s)")
if count_occurrences >= 2:
    # Replace all occurrences with empty, then re-add exactly one back
    content = content.replace(old_charge_fee, "", count_occurrences)
    # We need to keep exactly one copy — re-insert before pay_direct_referral_bonus
    anchor = "def pay_direct_referral_bonus(user_id: str, currency: str, amount: float, source_type: str = \"bonus\"):"
    assert anchor in content, "pay_direct_referral_bonus anchor not found for re-insertion"
    content = content.replace(anchor, old_charge_fee + anchor, 1)
elif count_occurrences == 1:
    print("Only one copy found, nothing to deduplicate for charge_nft_mint_fee")
else:
    print("WARNING: charge_nft_mint_fee block not found at all, skipping")

with open("models.py", "w", encoding="utf-8") as f:
    f.write(content)

print("models.py: duplicate function definitions removed")
