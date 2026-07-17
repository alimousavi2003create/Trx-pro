with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

old_import = "from models import get_or_create_user, get_user, update_balance, get_inventory, get_transactions, place_in_binary_tree, distribute_referral"
assert old_import in content, "models import anchor not found"
new_import = old_import + ", get_downline_count_by_side"
content = content.replace(old_import, new_import, 1)

old_route = '''    downline_count = get_downline_count(user_id)
    return jsonify({
        "success": True,
        "downline_count": downline_count,
        "left_commission_trx": float(user.get("left_commission_trx") or 0),
        "right_commission_trx": float(user.get("right_commission_trx") or 0),
    })'''
assert old_route in content, "referral stats route body anchor not found"
new_route = '''    downline_count = get_downline_count(user_id)
    left_downline_count, right_downline_count = get_downline_count_by_side(user_id)
    return jsonify({
        "success": True,
        "downline_count": downline_count,
        "left_downline_count": left_downline_count,
        "right_downline_count": right_downline_count,
        "left_commission_trx": float(user.get("left_commission_trx") or 0),
        "right_commission_trx": float(user.get("right_commission_trx") or 0),
    })'''
content = content.replace(old_route, new_route, 1)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("main.py: referral stats route updated with left/right downline counts")
