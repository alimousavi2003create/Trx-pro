with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

old_check = '''    if user["tap_count_today"] >= config.TAP_DAILY_LIMIT:
        return jsonify({"success": False, "error": "Daily tap limit reached"}), 400'''
new_check = '''    from datetime import datetime, timezone, timedelta
    reset_at = user.get("tap_count_reset_at")
    needs_reset = True
    if reset_at:
        if reset_at.tzinfo is None:
            reset_at = reset_at.replace(tzinfo=timezone.utc)
        needs_reset = (datetime.now(timezone.utc) - reset_at) >= timedelta(hours=24)
    if needs_reset:
        with get_db_cursor() as c:
            c.execute("UPDATE users SET tap_count_today = 0, tap_count_reset_at = NOW() WHERE user_id = %s",
                      (user_id,))
        user["tap_count_today"] = 0
    if user["tap_count_today"] >= config.TAP_DAILY_LIMIT:
        return jsonify({"success": False, "error": "Daily tap limit reached"}), 400'''
assert old_check in content, "tap_count_today check anchor not found"
content = content.replace(old_check, new_check, 1)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("main.py tap reset logic patch applied successfully")
