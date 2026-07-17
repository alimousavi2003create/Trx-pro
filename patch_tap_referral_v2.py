with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

old_end = '''        c.execute("""
            INSERT INTO transactions (user_id, type, currency, amount, balance_after, metadata)
            VALUES (%s, 'tap', 'TRX', %s, %s, %s)
        """, (user_id, reward, updated["balance_trx"] + reward,
              json.dumps({"mining_power": user["mining_power"]})))
    return jsonify({
        "success": True, "reward": reward,
        "balance_trx": updated["balance_trx"] + reward,
        "energy": updated["energy"], "tap_count_today": updated["tap_count_today"],
        "xp": updated["xp"], "level": updated["level"], "xp_next": updated["xp_next"]
    })'''

new_end = '''        c.execute("""
            INSERT INTO transactions (user_id, type, currency, amount, balance_after, metadata)
            VALUES (%s, 'tap', 'TRX', %s, %s, %s)
        """, (user_id, reward, updated["balance_trx"] + reward,
              json.dumps({"mining_power": user["mining_power"]})))

    try:
        pay_direct_referral_bonus(user_id, "TRX", reward, "tap")
    except Exception as e:
        logger.error(f"tap referral bonus failed: {e}")

    return jsonify({
        "success": True, "reward": reward,
        "balance_trx": updated["balance_trx"] + reward,
        "energy": updated["energy"], "tap_count_today": updated["tap_count_today"],
        "xp": updated["xp"], "level": updated["level"], "xp_next": updated["xp_next"]
    })'''

assert old_end in content, "tap function full end anchor not found"
count = content.count(old_end)
assert count == 1, f"anchor appears {count} times, must be exactly 1"
content = content.replace(old_end, new_end, 1)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)
print("main.py: tap referral bonus correctly hooked (v2)")
