import re

with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

# 1) import new functions
old_models_import = "from models import get_or_create_user, get_user, update_balance, get_inventory, get_transactions"
new_models_import = "from models import get_or_create_user, get_user, update_balance, get_inventory, get_transactions, place_in_binary_tree, distribute_referral"
assert old_models_import in content, "models import anchor not found"
content = content.replace(old_models_import, new_models_import, 1)

# 2) capture referral code on /start and place in tree
old_start_body = '''    user = update.effective_user
    get_or_create_user(
        user_id=str(user.id), username=user.username or "",
        first_name=user.first_name or "", last_name=user.last_name or "", photo_url=""
    )
    if not is_group_member(str(user.id)):'''
new_start_body = '''    user = update.effective_user
    existing = get_user(str(user.id))
    is_new_user = existing is None
    get_or_create_user(
        user_id=str(user.id), username=user.username or "",
        first_name=user.first_name or "", last_name=user.last_name or "", photo_url=""
    )
    if is_new_user and context.args:
        ref_code = context.args[0].strip()
        try:
            place_in_binary_tree(str(user.id), ref_code)
        except Exception as e:
            logger.error(f"referral placement failed: {e}")
    if not is_group_member(str(user.id)):'''
assert old_start_body in content, "start body anchor not found"
content = content.replace(old_start_body, new_start_body, 1)

# 3) call distribute_referral after crash cashout, before notify_group
old_cashout_notify = '''    notify_group(f"\\U0001F7E2 Someone won {net_payout:.2f} {bet['currency']} at {multiplier:.2f}x!")

    return jsonify({"success": True, "multiplier": multiplier, "payout": net_payout})'''
new_cashout_notify = '''    try:
        distribute_referral(user_id, bet["currency"], bet["amount"])
    except Exception as e:
        logger.error(f"referral distribution failed: {e}")

    notify_group(f"\\U0001F7E2 Someone won {net_payout:.2f} {bet['currency']} at {multiplier:.2f}x!")

    return jsonify({"success": True, "multiplier": multiplier, "payout": net_payout})'''
assert old_cashout_notify in content, "cashout notify anchor not found"
content = content.replace(old_cashout_notify, new_cashout_notify, 1)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("main.py referral patch applied successfully")
