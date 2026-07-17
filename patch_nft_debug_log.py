with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

old_start = '''@app.route("/api/nft/mint", methods=["POST"])
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
        return jsonify({"success": False, "error": fee_result["error"]}), 400'''

new_start = '''@app.route("/api/nft/mint", methods=["POST"])
def api_nft_mint():
    data = request.json
    user_id = str(data.get("user_id", ""))
    name = str(data.get("name", "")).strip()
    currency = str(data.get("currency", "")).upper()
    image_data = data.get("image_data", "")

    logger.info(f"NFT_MINT_DEBUG user_id={user_id} name_len={len(name)} currency={currency} image_len={len(image_data) if image_data else 0} image_prefix={image_data[:30] if image_data else None}")

    if not user_id or not name:
        logger.info("NFT_MINT_DEBUG rejected: missing name/user_id")
        return jsonify({"success": False, "error": "Name is required"}), 400
    if len(name) > 40:
        logger.info("NFT_MINT_DEBUG rejected: name too long")
        return jsonify({"success": False, "error": "Name too long (max 40 chars)"}), 400
    if currency not in ("TRX", "TON", "USDT"):
        logger.info(f"NFT_MINT_DEBUG rejected: bad currency {currency}")
        return jsonify({"success": False, "error": "Currency must be TRX, TON or USDT"}), 400
    if not image_data or not image_data.startswith("data:image/"):
        logger.info("NFT_MINT_DEBUG rejected: invalid image_data format")
        return jsonify({"success": False, "error": "Valid image required"}), 400
    if len(image_data) > config.NFT_MAX_IMAGE_BYTES:
        logger.info(f"NFT_MINT_DEBUG rejected: image too large, len={len(image_data)} limit={config.NFT_MAX_IMAGE_BYTES}")
        return jsonify({"success": False, "error": "Image too large (max 5MB)"}), 400

    user = get_user(user_id)
    if not user:
        logger.info(f"NFT_MINT_DEBUG rejected: user not found {user_id}")
        return jsonify({"success": False, "error": "User not found"}), 404

    fee_result = charge_nft_mint_fee(user_id, currency)
    if not fee_result["success"]:
        logger.info(f"NFT_MINT_DEBUG rejected: fee charge failed - {fee_result['error']}")
        return jsonify({"success": False, "error": fee_result["error"]}), 400'''

assert old_start in content, "nft mint route anchor not found - may already be patched or differ"
content = content.replace(old_start, new_start, 1)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("main.py patched with NFT mint debug logging")
