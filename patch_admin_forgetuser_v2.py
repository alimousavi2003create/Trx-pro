with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1) Insert the new function definition BEFORE admin_resetpool's own definition (module level, unindented)
func_anchor = "async def admin_resetpool(update: Update, context: ContextTypes.DEFAULT_TYPE):"
assert func_anchor in content, "admin_resetpool function definition anchor not found"

new_function = '''async def admin_forgetuser(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

content = content.replace(func_anchor, new_function + func_anchor, 1)

# 2) Register the handler right after the resetpool handler registration (indented context preserved)
handler_anchor = 'app_bot.add_handler(CommandHandler("resetpool", admin_resetpool))'
assert handler_anchor in content, "resetpool handler registration anchor not found"
new_handler_reg = (handler_anchor + '\n'
                    '    app_bot.add_handler(CommandHandler("forgetuser", admin_forgetuser))')
content = content.replace(handler_anchor, new_handler_reg, 1)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("main.py patched with /forgetuser admin command (v2, correct placement)")
