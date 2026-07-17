# 1) main.py - import new functions + hook into tap
with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

old_import = ("from models import get_or_create_user, get_user, update_balance, get_inventory, get_transactions, "
              "place_in_binary_tree, distribute_referral, create_nft, get_nft, get_user_nfts, "
              "get_marketplace_listings, set_nft_listing, transfer_nft, charge_nft_mint_fee, delete_nft")
new_import = ("from models import get_or_create_user, get_user, update_balance, get_inventory, get_transactions, "
              "place_in_binary_tree, distribute_referral, create_nft, get_nft, get_user_nfts, "
              "get_marketplace_listings, set_nft_listing, transfer_nft, charge_nft_mint_fee, delete_nft, "
              "pay_direct_referral_bonus, get_downline_count")
assert old_import in content, "models import anchor not found"
content = content.replace(old_import, new_import, 1)

old_tap_end = '''            c.execute("""
                UPDATE users SET level = %s, xp = 0, xp_next = %s, mining_power = mining_power + 0.5
                WHERE user_id = %s
            """, (new_level, new_xp_next, user_id))'''
new_tap_end = '''            c.execute("""
                UPDATE users SET level = %s, xp = 0, xp_next = %s, mining_power = mining_power + 0.5
                WHERE user_id = %s
            """, (new_level, new_xp_next, user_id))

    try:
        pay_direct_referral_bonus(user_id, "TRX", reward, "tap")
    except Exception as e:
        logger.error(f"tap referral bonus failed: {e}")'''
assert old_tap_end in content, "tap function end anchor not found"
content = content.replace(old_tap_end, new_tap_end, 1)

# 2) Add /api/referral/stats endpoint - insert before is_admin anchor
anchor = "def is_admin(telegram_user_id):"
assert anchor in content, "is_admin anchor not found"
new_route = '''@app.route("/api/referral/stats")
def api_referral_stats():
    user_id = request.args.get("user_id", "")
    if not user_id:
        return jsonify({"success": False, "error": "user_id required"}), 400
    user = get_user(user_id)
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404
    downline_count = get_downline_count(user_id)
    return jsonify({
        "success": True,
        "downline_count": downline_count,
        "left_commission_trx": float(user.get("left_commission_trx") or 0),
        "right_commission_trx": float(user.get("right_commission_trx") or 0),
    })


'''
content = content.replace(anchor, new_route + anchor, 1)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)
print("main.py: tap referral bonus + /api/referral/stats added")
