with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

old_block = '''    if is_new_user and context.args:
        ref_code = context.args[0].strip()
        try:
            place_in_binary_tree(str(user.id), ref_code)
        except Exception as e:
            logger.error(f"referral placement failed: {e}")'''

new_block = '''    logger.info(f"REFERRAL_DEBUG user_id={user.id} is_new_user={is_new_user} args={context.args}")
    if is_new_user and context.args:
        ref_code = context.args[0].strip()
        logger.info(f"REFERRAL_DEBUG attempting placement, ref_code={ref_code}")
        try:
            placed = place_in_binary_tree(str(user.id), ref_code)
            logger.info(f"REFERRAL_DEBUG placement result={placed}")
        except Exception as e:
            logger.error(f"REFERRAL_DEBUG placement failed: {e}")
    elif not is_new_user:
        logger.info(f"REFERRAL_DEBUG skipped placement: user {user.id} already existed in database")
    elif not context.args:
        logger.info(f"REFERRAL_DEBUG skipped placement: no start parameter received")'''

assert old_block in content, "referral placement anchor not found"
content = content.replace(old_block, new_block, 1)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("main.py patched with referral debug logging")
