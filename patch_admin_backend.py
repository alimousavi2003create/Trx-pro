import re

with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

anchor = "def is_admin(telegram_user_id):"
if anchor not in content:
    raise SystemExit("Anchor not found in main.py - aborting, no changes made")

new_routes = '''@app.route("/api/admin/check")
def api_admin_check():
    user_id = request.args.get("user_id", "")
    return jsonify({"success": True, "is_admin": str(user_id) in config.ADMIN_TELEGRAM_IDS})


@app.route("/api/admin/dashboard")
def api_admin_dashboard():
    admin_id = request.args.get("admin_id", "")
    if str(admin_id) not in config.ADMIN_TELEGRAM_IDS:
        return jsonify({"success": False, "error": "Admin access required"}), 403
    with get_db_cursor() as c:
        c.execute("SELECT COUNT(*) as cnt FROM users")
        total_users = c.fetchone()["cnt"]
        c.execute("SELECT * FROM withdrawal_requests WHERE status = %s ORDER BY created_at ASC LIMIT 50", ("pending",))
        pending_withdrawals = [dict(row) for row in c.fetchall()]
        c.execute("SELECT currency, total_collected, total_paid FROM pool_state")
        pool = [dict(row) for row in c.fetchall()]
        c.execute("SELECT * FROM transactions ORDER BY created_at DESC LIMIT 20")
        recent_tx = [dict(row) for row in c.fetchall()]
    return jsonify({
        "success": True,
        "total_users": total_users,
        "pending_withdrawals": pending_withdrawals,
        "pool": pool,
        "recent_transactions": recent_tx,
    })


@app.route("/api/admin/withdraw/approve", methods=["POST"])
def api_admin_withdraw_approve():
    data = request.json
    admin_id = str(data.get("admin_id", ""))
    if admin_id not in config.ADMIN_TELEGRAM_IDS:
        return jsonify({"success": False, "error": "Admin access required"}), 403
    wid = data.get("withdrawal_id")
    with get_db_cursor() as c:
        c.execute("SELECT * FROM withdrawal_requests WHERE id = %s AND status = 'pending'", (wid,))
        req = c.fetchone()
        if not req:
            return jsonify({"success": False, "error": "Request not found or already processed"}), 404
        c.execute("UPDATE withdrawal_requests SET status = 'paid', processed_at = NOW() WHERE id = %s", (wid,))
        c.execute("""
            INSERT INTO transactions (user_id, type, currency, amount, metadata)
            VALUES (%s, 'withdrawal_paid', %s, %s, %s)
        """, (req["user_id"], req["currency"], -req["amount"], json.dumps({"withdrawal_id": wid, "admin_id": admin_id})))
    return jsonify({"success": True, "message": f"Withdrawal #{wid} approved"})


@app.route("/api/admin/withdraw/reject", methods=["POST"])
def api_admin_withdraw_reject():
    data = request.json
    admin_id = str(data.get("admin_id", ""))
    if admin_id not in config.ADMIN_TELEGRAM_IDS:
        return jsonify({"success": False, "error": "Admin access required"}), 403
    wid = data.get("withdrawal_id")
    with get_db_cursor() as c:
        c.execute("SELECT * FROM withdrawal_requests WHERE id = %s AND status = 'pending'", (wid,))
        req = c.fetchone()
        if not req:
            return jsonify({"success": False, "error": "Request not found or already processed"}), 404
        balance_col = get_balance_col(req["currency"])
        c.execute(f"UPDATE users SET {balance_col} = {balance_col} + %s WHERE user_id = %s",
                   (req["amount"], req["user_id"]))
        c.execute("UPDATE withdrawal_requests SET status = 'rejected', processed_at = NOW() WHERE id = %s", (wid,))
    return jsonify({"success": True, "message": f"Withdrawal #{wid} rejected and refunded"})


@app.route("/api/admin/credit", methods=["POST"])
def api_admin_credit():
    data = request.json
    admin_id = str(data.get("admin_id", ""))
    if admin_id not in config.ADMIN_TELEGRAM_IDS:
        return jsonify({"success": False, "error": "Admin access required"}), 403
    target_user_id = str(data.get("target_user_id", ""))
    currency = str(data.get("currency", "")).upper()
    amount = data.get("amount")
    if currency not in ("TRX", "TON", "USDT"):
        return jsonify({"success": False, "error": "Currency must be TRX, TON or USDT"}), 400
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Invalid amount"}), 400
    user = get_user(target_user_id)
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404
    balance_col = get_balance_col(currency)
    with get_db_cursor() as c:
        c.execute(f"UPDATE users SET {balance_col} = {balance_col} + %s WHERE user_id = %s",
                   (amount, target_user_id))
        c.execute("""
            INSERT INTO transactions (user_id, type, currency, amount, metadata)
            VALUES (%s, 'admin_credit', %s, %s, %s)
        """, (target_user_id, currency, amount, json.dumps({"admin_id": admin_id})))
    return jsonify({"success": True, "message": f"Credited {amount} {currency} to {target_user_id}"})


@app.route("/api/admin/resetpool", methods=["POST"])
def api_admin_resetpool():
    data = request.json
    admin_id = str(data.get("admin_id", ""))
    if admin_id not in config.ADMIN_TELEGRAM_IDS:
        return jsonify({"success": False, "error": "Admin access required"}), 403
    with get_db_cursor() as c:
        c.execute("UPDATE pool_state SET total_collected = 0, total_paid = 0")
    return jsonify({"success": True, "message": "Pool reset"})


'''

content = content.replace(anchor, new_routes + anchor, 1)

old_credit_check = '''    if currency not in ("TRX", "TON"):
        await update.message.reply_text("Currency must be TRX or TON.")
        return'''
new_credit_check = '''    if currency not in ("TRX", "TON", "USDT"):
        await update.message.reply_text("Currency must be TRX, TON or USDT.")
        return'''

if old_credit_check in content:
    content = content.replace(old_credit_check, new_credit_check, 1)
else:
    print("WARNING: bot /credit currency check not found, skipped that fix")

old_usage = '"/credit <user_id> <TRX|TON> <amount> - manually credit a user"'
new_usage = '"/credit <user_id> <TRX|TON|USDT> <amount> - manually credit a user"'
if old_usage in content:
    content = content.replace(old_usage, new_usage, 1)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("main.py patched successfully")
