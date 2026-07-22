with open("crash_engine.py", "r", encoding="utf-8") as f:
    content = f.read()

old_block = '''def _settle_round():
    round_id = live_state["round_id"]
    cp = live_state["crash_point"]
    color = "\\U0001F7E2" if cp and cp >= 1.8 else "\\U0001F534"
    template = random.choice(ROUND_MESSAGE_TEMPLATES)
    msg = template.format(color=color, mult=cp)
    sticker_id = "CAACAgIAAxkBAAEBl2Zl0000000000000000000000000AAg" if cp and cp >= 2.0 else None
    notify_group(msg, sticker_id=sticker_id if False else None)
    with get_db_cursor() as c:'''

new_block = '''CELEBRATION_EMOJIS = [
    "\\U0001F96D", "\\U0001F34D", "\\U0001F34C", "\\U0001F34B", "\\U0001F34A", "\\U0001F349",
    "\\U0001F348", "\\U0001F347", "\\U0001F95D", "\\U0001FAD0", "\\U0001F353", "\\U0001F352",
    "\\U0001F351", "\\U0001F350", "\\U0001F34F", "\\U0001F34E", "\\U0001F345", "\\U0001FAD2",
    "\\U0001F965", "\\U0001F951", "\\U0001F346", "\\U0001F954", "\\U0001F955", "\\U0001F9C5",
    "\\U0001F9C4", "\\U0001F966", "\\U0001F96C", "\\U0001F952", "\\U0001F336", "\\U0001F33D",
    "\\U0001FAD1", "\\U0001FAD8", "\\U0001F95C", "\\U0001F35E", "\\U0001F950", "\\U0001F956",
    "\\U0001FAD3", "\\U0001F330", "\\U0001FADA", "\\U0001F968", "\\U0001F96F", "\\U0001F9C7",
    "\\U0001F9C0", "\\U0001F355", "\\U0001F35F", "\\U0001F354", "\\U0001F953", "\\U0001F969",
    "\\U0001F357", "\\U0001F32D", "\\U0001F96A", "\\U0001F32E", "\\U0001F32F",
    "\\U0001F95E", "\\U0001F366", "\\U0001F9C1", "\\U0001F36C", "\\U0001F36A",
    "\\U0001F36E", "\\U0001F37B", "\\U0001F964", "\\U0001F9C3", "\\U0001F379", "\\U0001F370",
    "\\U0001F3FA", "\\U0001F9CA", "\\U0001F374", "\\U0001F37D",
    "\\U0001F37E", "\\U0001F376",
]


def _settle_round():
    round_id = live_state["round_id"]
    cp = live_state["crash_point"]
    if cp and cp > 10:
        emoji = random.choice(CELEBRATION_EMOJIS)
        notify_group(f"{emoji} {cp}x!")
    with get_db_cursor() as c:'''

assert old_block in content, "_settle_round start anchor not found"
content = content.replace(old_block, new_block, 1)

old_loss_loop = '''    for row in lost_rows:
        if row["total"] and row["total"] > 0:
            notify_group(
                f"\\U0001F53B {row['cnt']} bettor(s) lost {row['total']:.2f} {row['currency']} (crashed at {live_state['crash_point']}x)"
            )'''
new_loss_loop = '''    # loss notifications removed to reduce group clutter (per request)'''
assert old_loss_loop in content, "loss notify loop anchor not found"
content = content.replace(old_loss_loop, new_loss_loop, 1)

with open("crash_engine.py", "w", encoding="utf-8") as f:
    f.write(content)
print("crash_engine.py: spammy messages replaced with rare >10x celebration emoji")
