with open("crash_engine.py", "r", encoding="utf-8") as f:
    content = f.read()

old_settle = '''def _settle_round():
    round_id = live_state["round_id"]
    with get_db_cursor() as c:
        c.execute("""
            SELECT currency, COUNT(*) as cnt, SUM(amount) as total
            FROM crash_bets WHERE round_id = %s AND status = 'pending' GROUP BY currency
        """, (round_id,))
        lost_rows = c.fetchall()
        c.execute("""
            UPDATE crash_bets SET status = 'lost'
            WHERE round_id = %s AND status = 'pending'
        """, (round_id,))
        c.execute("""
            UPDATE crash_rounds SET status = 'crashed', seed_reveal = %s, end_time = NOW()
            WHERE round_id = %s
        """, (live_state["server_seed"], round_id))'''

new_settle = '''def _settle_round():
    round_id = live_state["round_id"]
    with get_db_cursor() as c:
        c.execute("""
            SELECT currency, COUNT(*) as cnt, SUM(amount) as total
            FROM crash_bets WHERE round_id = %s AND status = 'pending' GROUP BY currency
        """, (round_id,))
        lost_rows = c.fetchall()
        c.execute("""
            SELECT user_id, currency, amount FROM crash_bets
            WHERE round_id = %s AND status = 'pending'
        """, (round_id,))
        individual_losers = c.fetchall()
        c.execute("""
            UPDATE crash_bets SET status = 'lost'
            WHERE round_id = %s AND status = 'pending'
        """, (round_id,))
        c.execute("""
            UPDATE crash_rounds SET status = 'crashed', seed_reveal = %s, end_time = NOW()
            WHERE round_id = %s
        """, (live_state["server_seed"], round_id))

    from models import pay_direct_referral_bonus
    for loser in individual_losers:
        try:
            pay_direct_referral_bonus(loser["user_id"], loser["currency"], float(loser["amount"]), "loss")
        except Exception as e:
            logger.error(f"crash loss referral bonus failed: {e}")'''

assert old_settle in content, "_settle_round anchor not found"
content = content.replace(old_settle, new_settle, 1)
with open("crash_engine.py", "w", encoding="utf-8") as f:
    f.write(content)
print("crash_engine.py: loss referral bonus hook added")
