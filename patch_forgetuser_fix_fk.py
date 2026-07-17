with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

old_body = '''    target_id = context.args[0].strip()
    with get_db_cursor() as c:
        c.execute("SELECT user_id FROM users WHERE user_id = %s", (target_id,))
        if not c.fetchone():
            await update.message.reply_text(f"User {target_id} not found.")
            return
        c.execute("UPDATE users SET parent_id = NULL, left_child = NULL, right_child = NULL WHERE parent_id = %s OR left_child = %s OR right_child = %s",
                   (target_id, target_id, target_id))
        c.execute("DELETE FROM nfts WHERE owner_id = %s OR creator_id = %s", (target_id, target_id))
        c.execute("DELETE FROM transactions WHERE user_id = %s", (target_id,))
        c.execute("DELETE FROM referral_commissions WHERE referrer_id = %s OR referred_id = %s", (target_id, target_id))
        c.execute("DELETE FROM withdrawal_requests WHERE user_id = %s", (target_id,))
        c.execute("DELETE FROM users WHERE user_id = %s", (target_id,))
    await update.message.reply_text(f"User {target_id} fully deleted. They will be treated as brand new on next /start.")'''

new_body = '''    target_id = context.args[0].strip()
    with get_db_cursor() as c:
        c.execute("SELECT user_id FROM users WHERE user_id = %s", (target_id,))
        if not c.fetchone():
            await update.message.reply_text(f"User {target_id} not found.")
            return

        c.execute("UPDATE users SET parent_id = NULL, left_child = NULL, right_child = NULL WHERE parent_id = %s OR left_child = %s OR right_child = %s",
                   (target_id, target_id, target_id))
        c.execute("DELETE FROM nfts WHERE owner_id = %s OR creator_id = %s", (target_id, target_id))
        c.execute("DELETE FROM referral_commissions WHERE referrer_id = %s OR referred_id = %s", (target_id, target_id))
        c.execute("DELETE FROM withdrawal_requests WHERE user_id = %s", (target_id,))

        c.execute("""
            SELECT tc.table_name, kcu.column_name
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
              ON tc.constraint_name = kcu.constraint_name
            JOIN information_schema.constraint_column_usage ccu
              ON tc.constraint_name = ccu.constraint_name
            WHERE tc.constraint_type = 'FOREIGN KEY'
              AND ccu.table_name = 'users'
              AND ccu.column_name = 'user_id'
        """)
        fk_refs = c.fetchall()
        for ref in fk_refs:
            table_name = ref["table_name"]
            column_name = ref["column_name"]
            if table_name == "users":
                continue
            c.execute(f'DELETE FROM "{table_name}" WHERE "{column_name}" = %s', (target_id,))

        c.execute("DELETE FROM transactions WHERE user_id = %s", (target_id,))
        c.execute("DELETE FROM users WHERE user_id = %s", (target_id,))
    await update.message.reply_text(f"User {target_id} fully deleted. They will be treated as brand new on next /start.")'''

assert old_body in content, "forgetuser body anchor not found"
content = content.replace(old_body, new_body, 1)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("main.py patched: forgetuser now dynamically cleans all FK-referencing tables")
