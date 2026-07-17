with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1) import delete_nft
old_import = ("from models import get_or_create_user, get_user, update_balance, get_inventory, get_transactions, "
              "place_in_binary_tree, distribute_referral, create_nft, get_nft, get_user_nfts, "
              "get_marketplace_listings, set_nft_listing, transfer_nft, charge_nft_mint_fee")
new_import = ("from models import get_or_create_user, get_user, update_balance, get_inventory, get_transactions, "
              "place_in_binary_tree, distribute_referral, create_nft, get_nft, get_user_nfts, "
              "get_marketplace_listings, set_nft_listing, transfer_nft, charge_nft_mint_fee, delete_nft")
assert old_import in content, "models import anchor not found"
content = content.replace(old_import, new_import, 1)

# 2) pass fee info to create_nft
old_create_call = '''    nft = create_nft(user_id, name, image_data)
    return jsonify({"success": True, "nft": nft, "fee_charged": fee_result["fee_charged"], "currency": currency})'''
new_create_call = '''    nft = create_nft(user_id, name, image_data, fee_result["fee_charged"], currency)
    return jsonify({"success": True, "nft": nft, "fee_charged": fee_result["fee_charged"], "currency": currency})'''
assert old_create_call in content, "create_nft call anchor not found"
content = content.replace(old_create_call, new_create_call, 1)

# 3) add delete route right after api_nft_buy
old_buy_end = '''    result = transfer_nft(nft_id, buyer_id)
    if not result["success"]:
        return jsonify(result), 400
    return jsonify(result)


'''
new_buy_end = '''    result = transfer_nft(nft_id, buyer_id)
    if not result["success"]:
        return jsonify(result), 400
    return jsonify(result)


@app.route("/api/nft/delete", methods=["POST"])
def api_nft_delete():
    data = request.json
    user_id = str(data.get("user_id", ""))
    nft_id = data.get("nft_id")
    if not user_id or not nft_id:
        return jsonify({"success": False, "error": "Missing parameters"}), 400
    result = delete_nft(nft_id, user_id)
    if not result["success"]:
        return jsonify(result), 403
    return jsonify(result)


'''
assert old_buy_end in content, "api_nft_buy end anchor not found"
content = content.replace(old_buy_end, new_buy_end, 1)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("main.py patched with nft delete route and fee tracking on mint")
