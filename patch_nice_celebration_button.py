with open("crash_engine.py", "r", encoding="utf-8") as f:
    content = f.read()

old_notify = '''def notify_group(text, sticker_id=None):
    try:
        requests.post(
            f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage",
            json={"chat_id": GROUP_CHAT_ID, "text": text},
            timeout=5,
        )
    except Exception as e:
        logger.error(f"notify_admin failed: {e}")'''

new_notify = '''def notify_group(text, sticker_id=None, reply_markup=None, parse_mode=None):
    try:
        payload = {"chat_id": GROUP_CHAT_ID, "text": text}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        if parse_mode:
            payload["parse_mode"] = parse_mode
        requests.post(
            f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage",
            json=payload,
            timeout=5,
        )
    except Exception as e:
        logger.error(f"notify_admin failed: {e}")'''

assert old_notify in content, "notify_group anchor not found"
content = content.replace(old_notify, new_notify, 1)

old_celebration = '''    if cp and cp > 10:
        emoji = random.choice(CELEBRATION_EMOJIS)
        notify_group(f"{emoji} {cp}x!")'''

new_celebration = '''    if cp and cp > 10:
        emoji = random.choice(CELEBRATION_EMOJIS)
        celebration_text = (
            f"{emoji} <b>{cp}x!</b>\\n"
            f"Someone just hit a huge multiplier in TRX PRO Crash!"
        )
        keyboard = {
            "inline_keyboard": [[
                {"text": "\\U0001F680 Play Now", "url": "https://t.me/Minerbyner_bot?start=celebration"}
            ]]
        }
        notify_group(celebration_text, reply_markup=keyboard, parse_mode="HTML")'''

assert old_celebration in content, "celebration block anchor not found"
content = content.replace(old_celebration, new_celebration, 1)

with open("crash_engine.py", "w", encoding="utf-8") as f:
    f.write(content)
print("crash_engine.py: nice celebration message with Play Now button added")
