with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()
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
print("main.py: /api/referral/stats route added")
