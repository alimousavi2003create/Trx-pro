import re

with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1) imports
old_import = "from telegram.ext import Application, CommandHandler, ContextTypes"
new_import = "from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes"
assert old_import in content, "telegram.ext import line not found"
content = content.replace(old_import, new_import, 1)

old_auth_import = "from auth import verify_init_data"
new_auth_import = "from auth import verify_init_data, is_group_member"
assert old_auth_import in content, "auth import line not found"
content = content.replace(old_auth_import, new_auth_import, 1)

# 2) gate api_auth_init
old_authinit = '''    user = get_or_create_user(
        user_id=verified["user_id"], username=verified["username"],
        first_name=verified["first_name"], last_name=verified["last_name"],
        photo_url=verified["photo_url"]
    )
    return jsonify({
        "success": True,
        "user": {'''
new_authinit = '''    user = get_or_create_user(
        user_id=verified["user_id"], username=verified["username"],
        first_name=verified["first_name"], last_name=verified["last_name"],
        photo_url=verified["photo_url"]
    )
    if not is_group_member(verified["user_id"]):
        return jsonify({
            "success": False, "error": "not_member",
            "join_url": config.FORCE_JOIN_INVITE_LINK
        }), 403
    return jsonify({
        "success": True,
        "user": {'''
assert old_authinit in content, "api_auth_init anchor not found"
content = content.replace(old_authinit, new_authinit, 1)

# 3) replace start() function and add callback handler, using regex to survive any whitespace quirks
pattern = re.compile(
    r"async def start\(update: Update, context: ContextTypes\.DEFAULT_TYPE\):.*?(?=\ndef run_flask\(\):)",
    re.DOTALL
)
match = pattern.search(content)
assert match, "start() function block not found"

new_start_block = '''async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    get_or_create_user(
        user_id=str(user.id), username=user.username or "",
        first_name=user.first_name or "", last_name=user.last_name or "", photo_url=""
    )
    if not is_group_member(str(user.id)):
        keyboard = [
            [InlineKeyboardButton("Join Group", url=config.FORCE_JOIN_INVITE_LINK)],
            [InlineKeyboardButton("I Joined - Check Again", callback_data="check_join")],
        ]
        await update.message.reply_text(
            "You must join our group before using TRX PRO.\\n\\n"
            "Tap Join Group, then come back and tap I Joined.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    keyboard = [[InlineKeyboardButton("Launch TRX PRO", web_app=WebAppInfo(url=config.WEBAPP_URL))]]
    await update.message.reply_text(
        f"Welcome to TRX PRO, {user.first_name}!\\n\\n"
        "Mine TRX by tapping\\n"
        "Buy powerful items\\n"
        "Play Crash game\\n"
        "Build your referral network\\n\\n"
        "Tap the button below to start:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def check_join_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    if not is_group_member(str(user.id)):
        await query.answer("You haven't joined yet.", show_alert=True)
        return
    keyboard = [[InlineKeyboardButton("Launch TRX PRO", web_app=WebAppInfo(url=config.WEBAPP_URL))]]
    await query.edit_message_text(
        f"Welcome to TRX PRO, {user.first_name}!\\n\\n"
        "Mine TRX by tapping\\n"
        "Buy powerful items\\n"
        "Play Crash game\\n"
        "Build your referral network\\n\\n"
        "Tap the button below to start:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

'''

content = content[:match.start()] + new_start_block + content[match.end():]

# 4) register callback handler
old_handler_reg = 'app_bot.add_handler(CommandHandler("resetpool", admin_resetpool))'
new_handler_reg = ('app_bot.add_handler(CommandHandler("resetpool", admin_resetpool))\n'
                    '    app_bot.add_handler(CallbackQueryHandler(check_join_callback, pattern="^check_join$"))')
assert old_handler_reg in content, "handler registration anchor not found"
content = content.replace(old_handler_reg, new_handler_reg, 1)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("main.py patched successfully")
