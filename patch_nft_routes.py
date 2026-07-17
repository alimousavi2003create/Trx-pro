with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

old_models_import = "from models import get_or_create_user, get_user, update_balance, get_inventory, get_transactions, place_in_binary_tree, distribute_referral"
new_models_import = ("from models import get_or_create_user, get_user, update_balance, get_inventory, get_transactions, "
                      "place_in_binary_tree, distribute_referral, create_nft, get_nft, get_user_nfts, "
                      "get_marketplace_listings, set_nft_listing, transfer_nft, charge_nft_mint_fee")
assert old_models_import in content, "models import anchor not found"
content = content.replace(old_models_import, new_models_import, 1)

anchor = "def is_admin(telegram_user_id):"
assert anchor in content, "is_admin anchor not found"

nft_routes = '''@app.route("/api/nft/mint", methods=["POST"])
def api_nft_mint():
    data = request.json
    user_id = str(data.get("user_id", ""))
    name = str(data.get("name", "")).strip()
    currency = str(data.get("currency", "")).upper()
    image_data = data.get("image_data", "")

    if not user_id or not name:
        return jsonify({"success": False, "error": "Name is required"}), 400
    if len(name) > 40:
        return jsonify({"success": False, "error": "Name too long (max 40 chars)"}), 400
    if currency not in ("TRX", "TON", "USDT"):
        return jsonify({"success": False, "error": "Currency must be TRX, TON or USDT"}), 400
    if not image_data or not image_data.startswith("data:image/"):
        return jsonify({"success": False, "error": "Valid image required"}), 400
    if len(image_data) > config.NFT_MAX_IMAGE_BYTES:
        return jsonify({"success": False, "error": "Image too large (max 2MB)"}), 400

    user = get_user(user_id)
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404

    fee_result = charge_nft_mint_fee(user_id, currency)
    if not fee_result["success"]:
        return jsonify({"success": False, "error": fee_result["error"]}), 400

    nft = create_nft(user_id, name, image_data)
    return jsonify({"success": True, "nft": nft, "fee_charged": fee_result["fee_charged"], "currency": currency})


@app.route("/api/nft/mine")
def api_nft_mine():
    user_id = request.args.get("user_id", "")
    if not user_id:
        return jsonify({"success": False, "error": "user_id required"}), 400
    nfts = get_user_nfts(user_id)
    return jsonify({"success": True, "nfts": nfts})


@app.route("/api/nft/market")
def api_nft_market():
    listings = get_marketplace_listings()
    return jsonify({"success": True, "listings": listings})


@app.route("/api/nft/image/<int:nft_id>")
def api_nft_image(nft_id):
    nft = get_nft(nft_id)
    if not nft:
        return jsonify({"success": False, "error": "NFT not found"}), 404
    return jsonify({"success": True, "image_data": nft["image_data"]})


@app.route("/api/nft/list", methods=["POST"])
def api_nft_list():
    data = request.json
    user_id = str(data.get("user_id", ""))
    nft_id = data.get("nft_id")
    price = data.get("price")
    currency = str(data.get("currency", "")).upper()
    is_listed = bool(data.get("is_listed", True))

    if currency not in ("TRX", "TON", "USDT"):
        return jsonify({"success": False, "error": "Currency must be TRX, TON or USDT"}), 400
    try:
        price = float(price)
        if price <= 0:
            raise ValueError()
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Invalid price"}), 400

    ok = set_nft_listing(nft_id, user_id, price, currency, is_listed)
    if not ok:
        return jsonify({"success": False, "error": "NFT not found or not owned by you"}), 403
    return jsonify({"success": True, "message": "Listing updated"})


@app.route("/api/nft/unlist", methods=["POST"])
def api_nft_unlist():
    data = request.json
    user_id = str(data.get("user_id", ""))
    nft_id = data.get("nft_id")
    nft = get_nft(nft_id)
    if not nft or nft["owner_id"] != user_id:
        return jsonify({"success": False, "error": "NFT not found or not owned by you"}), 403
    ok = set_nft_listing(nft_id, user_id, None, None, False)
    return jsonify({"success": ok})


@app.route("/api/nft/buy", methods=["POST"])
def api_nft_buy():
    data = request.json
    buyer_id = str(data.get("user_id", ""))
    nft_id = data.get("nft_id")
    if not buyer_id or not nft_id:
        return jsonify({"success": False, "error": "Missing parameters"}), 400
    result = transfer_nft(nft_id, buyer_id)
    if not result["success"]:
        return jsonify(result), 400
    return jsonify(result)


'''

content = content.replace(anchor, nft_routes + anchor, 1)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("main.py patched with NFT routes successfully")
