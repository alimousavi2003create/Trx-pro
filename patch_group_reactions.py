with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

old_imports = '''from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes'''
new_imports = '''from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo, ReactionTypeEmoji
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from crash_engine import GROUP_CHAT_ID'''
assert old_imports in content, "telegram imports anchor not found"
content = content.replace(old_imports, new_imports, 1)

func_anchor = "async def admin_resetpool(update: Update, context: ContextTypes.DEFAULT_TYPE):"
assert func_anchor in content, "admin_resetpool anchor not found"
new_function = '''async def react_to_group_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await context.bot.set_message_reaction(
            chat_id=update.effective_chat.id,
            message_id=update.message.message_id,
            reaction=[ReactionTypeEmoji("\\u2764")]
        )
    except Exception as e:
        logger.error(f"group message reaction failed: {e}")


'''
content = content.replace(func_anchor, new_function + func_anchor, 1)

handler_anchor = 'app_bot.add_handler(CommandHandler("mentionbatch", admin_mentionbatch))'
assert handler_anchor in content, "mentionbatch handler anchor not found"
new_handler_reg = (handler_anchor + '\n'
                    '    app_bot.add_handler(MessageHandler(filters.Chat(chat_id=int(GROUP_CHAT_ID)) & filters.ALL, react_to_group_messages))')
content = content.replace(handler_anchor, new_handler_reg, 1)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)
print("main.py: group reaction handler added")
