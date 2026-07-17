with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

anchor = 'app_bot.add_handler(CommandHandler("resetpool", admin_resetpool))'
assert anchor in content, "resetpool handler anchor not found"

new_command_fn = '''async def admin_forgetuser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(str(update.effective_user.id)):
        return
    if not context.args:
        await update.message.reply_text("Usage: /forgetuser <user_id>")
        return
    target_id = context.args[0].strip()
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
    await update.message.reply_text(f"User {target_id} fully deleted. They will be treated as brand new on next /start.")


'''

content = content.replace(anchor, new_command_fn.rstrip() + "\n\n\n" + anchor, 1)

new_handler_reg = f'{anchor}\n    app_bot.add_handler(CommandHandler("forgetuser", admin_forgetuser))'
content = content.replace(anchor, new_handler_reg, 1)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("main.py patched with /forgetuser admin command")
