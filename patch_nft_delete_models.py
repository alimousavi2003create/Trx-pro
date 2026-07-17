with open("models.py", "r", encoding="utf-8") as f:
    content = f.read()

old_create = '''def create_nft(owner_id: str, name: str, image_data: str):
    with get_db_cursor() as c:
        c.execute("""
            INSERT INTO nfts (owner_id, creator_id, name, image_data, is_listed)
            VALUES (%s, %s, %s, %s, FALSE)
            RETURNING id, owner_id, creator_id, name, price, currency, is_listed, created_at
        """, (owner_id, owner_id, name, image_data))
        row = c.fetchone()
        return dict(row) if row else None'''

new_create = '''def create_nft(owner_id: str, name: str, image_data: str, mint_fee_amount: float = None, mint_fee_currency: str = None):
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
    return {"success": True, "refunded_amount": refunded_amount, "refunded_currency": refunded_currency}'''

assert old_create in content, "create_nft function anchor not found"
content = content.replace(old_create, new_create, 1)

with open("models.py", "w", encoding="utf-8") as f:
    f.write(content)

print("models.py patched with delete_nft + mint fee tracking")
