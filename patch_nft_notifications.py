with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

old_list_end = '''    ok = set_nft_listing(nft_id, user_id, price, currency, is_listed)
    if not ok:
        return jsonify({"success": False, "error": "NFT not found or not owned by you"}), 403
    return jsonify({"success": True, "message": "Listing updated"})'''
assert old_list_end in content, "nft list end anchor not found"
new_list_end = '''    ok = set_nft_listing(nft_id, user_id, price, currency, is_listed)
    if not ok:
        return jsonify({"success": False, "error": "NFT not found or not owned by you"}), 403
    if is_listed:
        nft_info = get_nft(nft_id)
        nft_name = nft_info["name"] if nft_info else "an NFT"
        notify_group(f"\\U0001F5BC New NFT listed: {nft_name} for {price} {currency}!")
    return jsonify({"success": True, "message": "Listing updated"})'''
content = content.replace(old_list_end, new_list_end, 1)

old_buy_end = '''    result = transfer_nft(nft_id, buyer_id)
    if not result["success"]:
        return jsonify(result), 400
    return jsonify(result)'''
assert old_buy_end in content, "nft buy end anchor not found"
new_buy_end = '''    nft_before = get_nft(nft_id)
    result = transfer_nft(nft_id, buyer_id)
    if not result["success"]:
        return jsonify(result), 400
    if nft_before:
        notify_group(f"\\U0001F91D NFT \\\"{nft_before['name']}\\\" sold for {nft_before['price']} {nft_before['currency']}!")
    return jsonify(result)'''
content = content.replace(old_buy_end, new_buy_end, 1)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("main.py: NFT listing/sale notifications added")
