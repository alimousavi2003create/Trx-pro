with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

anchor = "async def admin_resetpool(update: Update, context: ContextTypes.DEFAULT_TYPE):"
assert anchor in content, "admin_resetpool anchor not found"

new_command = '''async def admin_mentionbatch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    count = 500
    if context.args:
        try:
            count = int(context.args[0])
        except ValueError:
            await update.message.reply_text("Usage: /mentionbatch <count> (default 500)")
            return
    with get_db_cursor() as c:
        c.execute("""
            SELECT user_id, username, first_name FROM users
            ORDER BY last_mentioned_at ASC NULLS FIRST
            LIMIT %s
        """, (count,))
        rows = c.fetchall()
    if not rows:
        await update.message.reply_text("No users found.")
        return

    mentions = []
    for row in rows:
        name = (row["first_name"] or "User").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        mentions.append(f'<a href="tg://user?id={row["user_id"]}">{name}</a>')

    chunks = []
    current_chunk = "New update on TRX PRO! Check it out:\\n\\n"
    for mention in mentions:
        if len(current_chunk) + len(mention) + 2 > 3500:
            chunks.append(current_chunk)
            current_chunk = ""
        current_chunk += mention + " "
    if current_chunk.strip():
        chunks.append(current_chunk)

    from crash_engine import GROUP_CHAT_ID
    import requests as req_lib
    sent_count = 0
    for chunk in chunks:
        try:
            req_lib.post(
                f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage",
                json={"chat_id": GROUP_CHAT_ID, "text": chunk, "parse_mode": "HTML"},
                timeout=10,
            )
            sent_count += 1
        except Exception as e:
            logger.error(f"mentionbatch send failed: {e}")

    user_ids = [row["user_id"] for row in rows]
    with get_db_cursor() as c:
        c.execute("UPDATE users SET last_mentioned_at = NOW() WHERE user_id = ANY(%s)", (user_ids,))

    await update.message.reply_text(f"Mentioned {len(rows)} users across {sent_count} message(s).")


'''
content = content.replace(anchor, new_command + anchor, 1)

old_handler_reg = 'app_bot.add_handler(CallbackQueryHandler(check_join_callback, pattern="^check_join$"))'
new_handler_reg = ('app_bot.add_handler(CallbackQueryHandler(check_join_callback, pattern="^check_join$"))\n'
                    '    app_bot.add_handler(CommandHandler("mentionbatch", admin_mentionbatch))')
assert old_handler_reg in content, "handler registration anchor not found"
content = content.replace(old_handler_reg, new_handler_reg, 1)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("main.py: /mentionbatch command added")
