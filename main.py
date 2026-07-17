"""TRX PRO - Main Application"""
import os
import time
import uuid
import json
import asyncio
import threading
import logging
from flask import Flask, request, jsonify, render_template
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

import config
from database import init_db, get_db_cursor
from auth import verify_init_data, is_group_member
from models import get_or_create_user, get_user, update_balance, get_inventory, get_transactions, place_in_binary_tree, distribute_referral, create_nft, get_nft, get_user_nfts, get_marketplace_listings, set_nft_listing, transfer_nft, charge_nft_mint_fee, delete_nft, pay_direct_referral_bonus, get_downline_count
from crash_engine import start_crash_engine, get_public_state, notify_group
from deposit_monitor import start_deposit_monitor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

def get_balance_col(currency):
    return {"TRX": "balance_trx", "TON": "balance_ton", "USDT": "balance_usdt"}.get(currency, "balance_trx")


@app.route("/")
def home():
    return render_template("index.html", bot_username=config.BOT_USERNAME)

@app.route("/tonconnect-manifest.json")
def manifest():
    return jsonify({
        "url": config.WEBAPP_URL,
        "name": "TRX PRO",
        "iconUrl": f"{config.WEBAPP_URL}/static/icons/logo.png",
    })

@app.route("/api/auth/init", methods=["POST"])
def api_auth_init():
    data = request.json
    init_data_raw = data.get("init_data", "")
    try:
        verified = verify_init_data(init_data_raw)
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 403
    user = get_or_create_user(
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
        "user": {
            "user_id": user["user_id"], "username": user["username"],
            "first_name": user["first_name"], "balance_trx": user["balance_trx"],
            "balance_ton": user["balance_ton"], "balance_usdt": user.get("balance_usdt", 0), "mining_power": user["mining_power"],
            "energy": user["energy"], "energy_max": user["energy_max"],
            "level": user["level"], "xp": user["xp"], "xp_next": user["xp_next"],
            "referral_code": user["referral_code"],
        }
    })

@app.route("/api/user/<user_id>")
def api_user(user_id):
    user = get_user(user_id)
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404
    inventory = get_inventory(user_id)
    return jsonify({
        "success": True,
        "user": {
            "user_id": user["user_id"], "username": user["username"],
            "first_name": user["first_name"], "balance_trx": user["balance_trx"],
            "balance_ton": user["balance_ton"], "balance_usdt": user.get("balance_usdt", 0), "mining_power": user["mining_power"],
            "energy": user["energy"], "energy_max": user["energy_max"],
            "level": user["level"], "xp": user["xp"], "xp_next": user["xp_next"],
            "referral_code": user["referral_code"],
            "left_volume": user["left_volume"], "right_volume": user["right_volume"],
            "cycle_count": user["cycle_count"],
        },
        "inventory": inventory
    })

@app.route("/api/tap", methods=["POST"])
def api_tap():
    data = request.json
    user_id = str(data.get("user_id"))
    init_data_raw = data.get("init_data", "")
    try:
        verify_init_data(init_data_raw)
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 403
    user = get_user(user_id)
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404
    if user["energy"] <= 0:
        return jsonify({"success": False, "error": "No energy left"}), 400
    from datetime import datetime, timezone, timedelta
    reset_at = user.get("tap_count_reset_at")
    needs_reset = True
    if reset_at:
        if reset_at.tzinfo is None:
            reset_at = reset_at.replace(tzinfo=timezone.utc)
        needs_reset = (datetime.now(timezone.utc) - reset_at) >= timedelta(hours=24)
    if needs_reset:
        with get_db_cursor() as c:
            c.execute("UPDATE users SET tap_count_today = 0, tap_count_reset_at = NOW() WHERE user_id = %s",
                      (user_id,))
        user["tap_count_today"] = 0
    if user["tap_count_today"] >= config.TAP_DAILY_LIMIT:
        return jsonify({"success": False, "error": "Daily tap limit reached"}), 400
    reward = config.TAP_BASE_REWARD * user["mining_power"]
    with get_db_cursor() as c:
        c.execute("""
            UPDATE users SET balance_trx = balance_trx + %s, energy = energy - 1,
                tap_count_today = tap_count_today + 1, tap_count_total = tap_count_total + 1,
                last_tap_at = NOW(), xp = xp + 1, last_active_at = NOW()
            WHERE user_id = %s RETURNING balance_trx, energy, tap_count_today, xp, level, xp_next
        """, (reward, user_id))
        updated = c.fetchone()
        if updated["xp"] >= updated["xp_next"]:
            new_level = updated["level"] + 1
            new_xp_next = int(config.LEVEL_UP_BASE_XP * (config.LEVEL_UP_MULTIPLIER ** new_level))
            c.execute("""
                UPDATE users SET level = %s, xp = 0, xp_next = %s, mining_power = mining_power + 0.5
                WHERE user_id = %s
            """, (new_level, new_xp_next, user_id))
            level_bonus = 50
            c.execute("UPDATE users SET balance_trx = balance_trx + %s WHERE user_id = %s",
                      (level_bonus, user_id))
            c.execute("""
                INSERT INTO transactions (user_id, type, currency, amount, metadata)
                VALUES (%s, 'level_up', 'TRX', %s, %s)
            """, (user_id, level_bonus, json.dumps({"new_level": new_level})))
        c.execute("""
            INSERT INTO transactions (user_id, type, currency, amount, balance_after, metadata)
            VALUES (%s, 'tap', 'TRX', %s, %s, %s)
        """, (user_id, reward, updated["balance_trx"] + reward,
              json.dumps({"mining_power": user["mining_power"]})))

    try:
        pay_direct_referral_bonus(user_id, "TRX", reward, "tap")
    except Exception as e:
        logger.error(f"tap referral bonus failed: {e}")

    return jsonify({
        "success": True, "reward": reward,
        "balance_trx": updated["balance_trx"] + reward,
        "energy": updated["energy"], "tap_count_today": updated["tap_count_today"],
        "xp": updated["xp"], "level": updated["level"], "xp_next": updated["xp_next"]
    })

@app.route("/api/shop/items")
def api_shop_items():
    with get_db_cursor() as c:
        c.execute("SELECT * FROM shop_items WHERE is_active = TRUE ORDER BY sort_order, rarity DESC")
        items = [dict(row) for row in c.fetchall()]
    return jsonify({"success": True, "items": items})

@app.route("/api/shop/buy", methods=["POST"])
def api_shop_buy():
    data = request.json
    user_id = str(data.get("user_id"))
    item_key = data.get("item_key")
    currency = data.get("currency", "TRX")
    user = get_user(user_id)
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404
    with get_db_cursor() as c:
        c.execute("SELECT * FROM shop_items WHERE item_key = %s AND is_active = TRUE", (item_key,))
        item = c.fetchone()
        if not item:
            return jsonify({"success": False, "error": "Item not found"}), 404
        if user["level"] < item["required_level"]:
            return jsonify({"success": False, "error": f"Requires level {item['required_level']}"}), 403
        price = item["price_trx"] if currency == "TRX" else item["price_ton"]
        if not price or price <= 0:
            return jsonify({"success": False, "error": "Invalid price"}), 400
        balance_col = get_balance_col(currency)
        c.execute(f"SELECT {balance_col} FROM users WHERE user_id = %s", (user_id,))
        bal = c.fetchone()[balance_col]
        if bal < price:
            return jsonify({"success": False, "error": "Insufficient balance"}), 400
        c.execute(f"UPDATE users SET {balance_col} = {balance_col} - %s WHERE user_id = %s",
                   (price, user_id))
        expires = None
        if item["effect_duration"] > 0:
            from datetime import datetime, timedelta
            expires = datetime.now() + timedelta(days=item["effect_duration"])
        c.execute("""
            INSERT INTO inventory (user_id, item_key, quantity, expires_at) VALUES (%s, %s, 1, %s)
        """, (user_id, item_key, expires))
        if item["effect_type"] == "energy":
            c.execute("""
                UPDATE users SET energy_max = energy_max + %s, energy = energy + %s WHERE user_id = %s
            """, (item["effect_value"], item["effect_value"], user_id))
        elif item["effect_type"] == "mining_speed":
            c.execute("""
                UPDATE users SET mining_power = mining_power + %s WHERE user_id = %s
            """, (item["effect_value"], user_id))
        fee = price * (config.PROJECT_FEE_PERCENT / 100)
        c.execute("""
            INSERT INTO transactions (user_id, type, currency, amount, fee, metadata)
            VALUES (%s, 'purchase', %s, %s, %s, %s)
        """, (user_id, currency, -price, fee, json.dumps({"item_key": item_key, "item_name": item["name"]})))
        return jsonify({
            "success": True, "message": f"Purchased {item['name']}",
            "balance_trx": user["balance_trx"] - (price if currency == "TRX" else 0),
            "balance_ton": user["balance_ton"] - (price if currency == "TON" else 0)
        })

@app.route("/api/admin/seed_shop", methods=["POST"])
def api_seed_shop():
    data = request.json
    if str(data.get("admin_id")) not in config.ADMIN_TELEGRAM_IDS:
        return jsonify({"success": False, "error": "Admin access required"}), 403
    default_items = [
        ("starter_miner_v1", "Starter Miner", "Auto-mine 0.15 TRX/hour for 10 days",
         "auto_mine", 0.15, 50, None, 10, "Common"),
        ("standard_miner_v1", "Standard Miner", "Auto-mine 0.3 TRX/hour for 15 days",
         "auto_mine", 0.3, 150, None, 15, "Rare"),
        ("pro_miner_v1", "Pro Miner", "Auto-mine 0.6 TRX/hour for 20 days",
         "auto_mine", 0.6, 400, None, 20, "Epic"),
        ("energy_core_v1", "Energy Core", "+50 Max Energy",
         "energy", 50, 200, None, 0, "Common"),
        ("trx_booster_v1", "TRX Booster", "+1.0 Mining Power",
         "mining_speed", 1.0, 300, None, 7, "Rare"),
        ("legendary_core", "Legendary Core", "+200 Max Energy & +2.0 Mining Power",
         "energy", 200, 3000, 2.0, 0, "Legendary"),
        ("speed_chip_v1", "Speed Chip", "+0.5 Mining Power",
         "mining_speed", 0.5, 150, None, 3, "Common"),
        ("power_core_v1", "Power Core", "+2.0 Mining Power",
         "mining_speed", 2.0, 800, None, 10, "Rare"),
        ("quantum_drill_v1", "Quantum Drill", "+5.0 Mining Power",
         "mining_speed", 5.0, 3000, 1.0, 21, "Epic"),
        ("smart_miner_v1", "Smart Miner", "Auto-mine 1.0 TRX per hour",
         "auto_mine", 1.0, 900, None, 30, "Rare"),
        ("energy_cell_v1", "Energy Cell", "+100 Max Energy",
         "energy", 100, 800, None, 0, "Rare"),
    ]
    with get_db_cursor() as c:
        for item in default_items:
            c.execute("""
                INSERT INTO shop_items (item_key, name, description, effect_type,
                                       effect_value, price_trx, price_ton, effect_duration, rarity)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (item_key) DO NOTHING
            """, item)
    return jsonify({"success": True, "message": "Shop items seeded"})

@app.route("/api/crash/state")
def api_crash_state():
    return jsonify({"success": True, **get_public_state()})

@app.route("/api/crash/bet", methods=["POST"])
def api_crash_bet():
    data = request.json
    user_id = str(data.get("user_id"))
    init_data_raw = data.get("init_data", "")
    currency = data.get("currency", "TRX")
    amount = data.get("amount")
    try:
        verify_init_data(init_data_raw)
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 403
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Invalid amount"}), 400
    if amount <= 0:
        return jsonify({"success": False, "error": "Invalid amount"}), 400

    state = get_public_state()
    if state["status"] != "waiting":
        return jsonify({"success": False, "error": "Betting closed for this round"}), 400

    user = get_user(user_id)
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404

    balance_col = get_balance_col(currency)
    if user[balance_col] < amount:
        return jsonify({"success": False, "error": "Insufficient balance"}), 400

    with get_db_cursor() as c:
        c.execute("SELECT id FROM crash_bets WHERE round_id = %s AND user_id = %s AND status = 'pending'",
                   (state["round_id"], user_id))
        if c.fetchone():
            return jsonify({"success": False, "error": "Bet already placed for this round"}), 400
        c.execute(f"UPDATE users SET {balance_col} = {balance_col} - %s WHERE user_id = %s",
                   (amount, user_id))
        c.execute("""
            INSERT INTO crash_bets (round_id, user_id, currency, amount, status)
            VALUES (%s, %s, %s, %s, 'pending')
        """, (state["round_id"], user_id, currency, amount))
        c.execute("""
            INSERT INTO pool_state (currency, total_collected, total_paid)
            VALUES (%s, %s, 0)
            ON CONFLICT (currency) DO UPDATE SET total_collected = pool_state.total_collected + %s
        """, (currency, amount, amount))

    return jsonify({"success": True, "message": "Bet placed"})

@app.route("/api/crash/cashout", methods=["POST"])
def api_crash_cashout():
    data = request.json
    user_id = str(data.get("user_id"))
    init_data_raw = data.get("init_data", "")
    try:
        verify_init_data(init_data_raw)
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 403

    state = get_public_state()
    if state["status"] != "running":
        return jsonify({"success": False, "error": "Round not running"}), 400

    with get_db_cursor() as c:
        c.execute("""
            SELECT * FROM crash_bets WHERE round_id = %s AND user_id = %s AND status = 'pending'
        """, (state["round_id"], user_id))
        bet = c.fetchone()
        if not bet:
            return jsonify({"success": False, "error": "No active bet"}), 400

        multiplier = state["multiplier"]
        payout = round(bet["amount"] * multiplier, 4)
        profit = round(payout - bet["amount"], 4)
        fee = round(profit * (config.PROJECT_FEE_PERCENT / 100), 4) if profit > 0 else 0
        net_payout = round(payout - fee, 4)
        balance_col = get_balance_col(bet["currency"])

        c.execute(f"UPDATE users SET {balance_col} = {balance_col} + %s WHERE user_id = %s",
                   (net_payout, user_id))
        c.execute("""
            UPDATE crash_bets SET status = 'cashed_out', cashout_multiplier = %s, profit = %s, fee = %s, cashed_out_at = NOW()
            WHERE id = %s
        """, (multiplier, profit, fee, bet["id"]))
        c.execute("""
            INSERT INTO transactions (user_id, type, currency, amount, fee, metadata)
            VALUES (%s, 'crash_win', %s, %s, %s, %s)
        """, (user_id, bet["currency"], net_payout, fee, json.dumps({"round_id": state["round_id"], "multiplier": multiplier})))
        c.execute("""
            INSERT INTO pool_state (currency, total_collected, total_paid)
            VALUES (%s, 0, %s)
            ON CONFLICT (currency) DO UPDATE SET total_paid = pool_state.total_paid + %s
        """, (bet["currency"], net_payout, net_payout))

    try:
        distribute_referral(user_id, bet["currency"], bet["amount"])
    except Exception as e:
        logger.error(f"referral distribution failed: {e}")

    notify_group(f"\U0001F7E2 Someone won {net_payout:.2f} {bet['currency']} at {multiplier:.2f}x!")

    return jsonify({"success": True, "multiplier": multiplier, "payout": net_payout})

@app.route("/api/deposit_info")
def api_deposit_info():
    return jsonify({
        "success": True,
        "wallets": {
            "TRX": config.PROJECT_WALLET_TRX,
            "TON": config.PROJECT_WALLET_TON,
            "USDT": config.PROJECT_WALLET_USDT,
        }
    })


@app.route("/api/withdraw", methods=["POST"])
def api_withdraw():
    data = request.json
    user_id = str(data.get("user_id"))
    init_data_raw = data.get("init_data", "")
    currency = data.get("currency", "TRX")
    amount = data.get("amount")
    destination = str(data.get("destination_address", "")).strip()
    try:
        verify_init_data(init_data_raw)
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 403
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Invalid amount"}), 400
    if amount <= 0 or not destination:
        return jsonify({"success": False, "error": "Invalid request"}), 400
    if currency == "TRX" and amount < config.MIN_WITHDRAWAL_TRX:
        return jsonify({"success": False, "error": f"Minimum withdrawal is {config.MIN_WITHDRAWAL_TRX} TRX"}), 400

    user = get_user(user_id)
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404
    balance_col = get_balance_col(currency)
    if user[balance_col] < amount:
        return jsonify({"success": False, "error": "Insufficient balance"}), 400

    with get_db_cursor() as c:
        c.execute(f"UPDATE users SET {balance_col} = {balance_col} - %s WHERE user_id = %s",
                   (amount, user_id))
        c.execute("""
            INSERT INTO withdrawal_requests (user_id, currency, amount, destination_address, status)
            VALUES (%s, %s, %s, %s, 'pending') RETURNING id
        """, (user_id, currency, amount, destination))
        wid = c.fetchone()["id"]
        c.execute("""
            INSERT INTO transactions (user_id, type, currency, amount, metadata)
            VALUES (%s, 'withdrawal_request', %s, %s, %s)
        """, (user_id, currency, -amount, json.dumps({"withdrawal_id": wid, "destination": destination})))

    return jsonify({"success": True, "message": "Withdrawal request submitted", "withdrawal_id": wid})


@app.route("/api/admin/check")
def api_admin_check():
    user_id = request.args.get("user_id", "")
    return jsonify({"success": True, "is_admin": str(user_id) in config.ADMIN_TELEGRAM_IDS})


@app.route("/api/admin/dashboard")
def api_admin_dashboard():
    admin_id = request.args.get("admin_id", "")
    if str(admin_id) not in config.ADMIN_TELEGRAM_IDS:
        return jsonify({"success": False, "error": "Admin access required"}), 403
    with get_db_cursor() as c:
        c.execute("SELECT COUNT(*) as cnt FROM users")
        total_users = c.fetchone()["cnt"]
        c.execute("SELECT * FROM withdrawal_requests WHERE status = %s ORDER BY created_at ASC LIMIT 50", ("pending",))
        pending_withdrawals = [dict(row) for row in c.fetchall()]
        c.execute("SELECT currency, total_collected, total_paid FROM pool_state")
        pool = [dict(row) for row in c.fetchall()]
        c.execute("SELECT * FROM transactions ORDER BY created_at DESC LIMIT 20")
        recent_tx = [dict(row) for row in c.fetchall()]
    return jsonify({
        "success": True,
        "total_users": total_users,
        "pending_withdrawals": pending_withdrawals,
        "pool": pool,
        "recent_transactions": recent_tx,
    })


@app.route("/api/admin/withdraw/approve", methods=["POST"])
def api_admin_withdraw_approve():
    data = request.json
    admin_id = str(data.get("admin_id", ""))
    if admin_id not in config.ADMIN_TELEGRAM_IDS:
        return jsonify({"success": False, "error": "Admin access required"}), 403
    wid = data.get("withdrawal_id")
    with get_db_cursor() as c:
        c.execute("SELECT * FROM withdrawal_requests WHERE id = %s AND status = 'pending'", (wid,))
        req = c.fetchone()
        if not req:
            return jsonify({"success": False, "error": "Request not found or already processed"}), 404
        c.execute("UPDATE withdrawal_requests SET status = 'paid', processed_at = NOW() WHERE id = %s", (wid,))
        c.execute("""
            INSERT INTO transactions (user_id, type, currency, amount, metadata)
            VALUES (%s, 'withdrawal_paid', %s, %s, %s)
        """, (req["user_id"], req["currency"], -req["amount"], json.dumps({"withdrawal_id": wid, "admin_id": admin_id})))
    return jsonify({"success": True, "message": f"Withdrawal #{wid} approved"})


@app.route("/api/admin/withdraw/reject", methods=["POST"])
def api_admin_withdraw_reject():
    data = request.json
    admin_id = str(data.get("admin_id", ""))
    if admin_id not in config.ADMIN_TELEGRAM_IDS:
        return jsonify({"success": False, "error": "Admin access required"}), 403
    wid = data.get("withdrawal_id")
    with get_db_cursor() as c:
        c.execute("SELECT * FROM withdrawal_requests WHERE id = %s AND status = 'pending'", (wid,))
        req = c.fetchone()
        if not req:
            return jsonify({"success": False, "error": "Request not found or already processed"}), 404
        balance_col = get_balance_col(req["currency"])
        c.execute(f"UPDATE users SET {balance_col} = {balance_col} + %s WHERE user_id = %s",
                   (req["amount"], req["user_id"]))
        c.execute("UPDATE withdrawal_requests SET status = 'rejected', processed_at = NOW() WHERE id = %s", (wid,))
    return jsonify({"success": True, "message": f"Withdrawal #{wid} rejected and refunded"})


@app.route("/api/admin/credit", methods=["POST"])
def api_admin_credit():
    data = request.json
    admin_id = str(data.get("admin_id", ""))
    if admin_id not in config.ADMIN_TELEGRAM_IDS:
        return jsonify({"success": False, "error": "Admin access required"}), 403
    target_user_id = str(data.get("target_user_id", ""))
    currency = str(data.get("currency", "")).upper()
    amount = data.get("amount")
    if currency not in ("TRX", "TON", "USDT"):
        return jsonify({"success": False, "error": "Currency must be TRX, TON or USDT"}), 400
    try:
        amount = float(amount)
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Invalid amount"}), 400
    user = get_user(target_user_id)
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404
    balance_col = get_balance_col(currency)
    with get_db_cursor() as c:
        c.execute(f"UPDATE users SET {balance_col} = {balance_col} + %s WHERE user_id = %s",
                   (amount, target_user_id))
        c.execute("""
            INSERT INTO transactions (user_id, type, currency, amount, metadata)
            VALUES (%s, 'admin_credit', %s, %s, %s)
        """, (target_user_id, currency, amount, json.dumps({"admin_id": admin_id})))
    return jsonify({"success": True, "message": f"Credited {amount} {currency} to {target_user_id}"})


@app.route("/api/admin/resetpool", methods=["POST"])
def api_admin_resetpool():
    data = request.json
    admin_id = str(data.get("admin_id", ""))
    if admin_id not in config.ADMIN_TELEGRAM_IDS:
        return jsonify({"success": False, "error": "Admin access required"}), 403
    with get_db_cursor() as c:
        c.execute("UPDATE pool_state SET total_collected = 0, total_paid = 0")
    return jsonify({"success": True, "message": "Pool reset"})


@app.route("/api/nft/mint", methods=["POST"])
def api_nft_mint():
    content_length = request.content_length
    logger.info(f"NFT_MINT_DEBUG raw request received, content_length={content_length}")
    data = request.get_json(silent=True)
    if data is None:
        raw_preview = request.get_data(as_text=True)[:200]
        logger.info(f"NFT_MINT_DEBUG JSON PARSE FAILED, content_length={content_length}, raw_preview={raw_preview}")
        return jsonify({"success": False, "error": "Invalid request body"}), 400
    user_id = str(data.get("user_id", ""))
    name = str(data.get("name", "")).strip()
    currency = str(data.get("currency", "")).upper()
    image_data = data.get("image_data", "")

    logger.info(f"NFT_MINT_DEBUG user_id={user_id} name_len={len(name)} currency={currency} image_len={len(image_data) if image_data else 0} image_prefix={image_data[:30] if image_data else None}")

    if not user_id or not name:
        logger.info("NFT_MINT_DEBUG rejected: missing name/user_id")
        return jsonify({"success": False, "error": "Name is required"}), 400
    if len(name) > 40:
        logger.info("NFT_MINT_DEBUG rejected: name too long")
        return jsonify({"success": False, "error": "Name too long (max 40 chars)"}), 400
    if currency not in ("TRX", "TON", "USDT"):
        logger.info(f"NFT_MINT_DEBUG rejected: bad currency {currency}")
        return jsonify({"success": False, "error": "Currency must be TRX, TON or USDT"}), 400
    if not image_data or not image_data.startswith("data:image/"):
        logger.info("NFT_MINT_DEBUG rejected: invalid image_data format")
        return jsonify({"success": False, "error": "Valid image required"}), 400
    if len(image_data) > config.NFT_MAX_IMAGE_BYTES:
        logger.info(f"NFT_MINT_DEBUG rejected: image too large, len={len(image_data)} limit={config.NFT_MAX_IMAGE_BYTES}")
        return jsonify({"success": False, "error": "Image too large (max 5MB)"}), 400

    user = get_user(user_id)
    if not user:
        logger.info(f"NFT_MINT_DEBUG rejected: user not found {user_id}")
        return jsonify({"success": False, "error": "User not found"}), 404

    fee_result = charge_nft_mint_fee(user_id, currency)
    if not fee_result["success"]:
        logger.info(f"NFT_MINT_DEBUG rejected: fee charge failed - {fee_result['error']}")
        return jsonify({"success": False, "error": fee_result["error"]}), 400

    nft = create_nft(user_id, name, image_data, fee_result["fee_charged"], currency)
    return jsonify({"success": True, "nft": nft, "fee_charged": fee_result["fee_charged"], "currency": currency})


@app.route("/api/nft/mine")
def api_nft_mine():
    user_id = request.args.get("user_id", "")
    if not user_id:
        return jsonify({"success": False, "error": "user_id required"}), 400
    nfts = get_user_nfts(user_id)
    return jsonify({"success": True, "nfts": nfts})


@app.route("/api/nft/market")
def api_nft_market():
    listings = get_marketplace_listings()
    return jsonify({"success": True, "listings": listings})


@app.route("/api/nft/image/<int:nft_id>")
def api_nft_image(nft_id):
    nft = get_nft(nft_id)
    if not nft:
        return jsonify({"success": False, "error": "NFT not found"}), 404
    return jsonify({"success": True, "image_data": nft["image_data"]})


@app.route("/api/nft/list", methods=["POST"])
def api_nft_list():
    data = request.json
    user_id = str(data.get("user_id", ""))
    nft_id = data.get("nft_id")
    price = data.get("price")
    currency = str(data.get("currency", "")).upper()
    is_listed = bool(data.get("is_listed", True))

    if currency not in ("TRX", "TON", "USDT"):
        return jsonify({"success": False, "error": "Currency must be TRX, TON or USDT"}), 400
    try:
        price = float(price)
        if price <= 0:
            raise ValueError()
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "Invalid price"}), 400

    ok = set_nft_listing(nft_id, user_id, price, currency, is_listed)
    if not ok:
        return jsonify({"success": False, "error": "NFT not found or not owned by you"}), 403
    return jsonify({"success": True, "message": "Listing updated"})


@app.route("/api/nft/unlist", methods=["POST"])
def api_nft_unlist():
    data = request.json
    user_id = str(data.get("user_id", ""))
    nft_id = data.get("nft_id")
    nft = get_nft(nft_id)
    if not nft or nft["owner_id"] != user_id:
        return jsonify({"success": False, "error": "NFT not found or not owned by you"}), 403
    ok = set_nft_listing(nft_id, user_id, None, None, False)
    return jsonify({"success": ok})


@app.route("/api/nft/buy", methods=["POST"])
def api_nft_buy():
    data = request.json
    buyer_id = str(data.get("user_id", ""))
    nft_id = data.get("nft_id")
    if not buyer_id or not nft_id:
        return jsonify({"success": False, "error": "Missing parameters"}), 400
    result = transfer_nft(nft_id, buyer_id)
    if not result["success"]:
        return jsonify(result), 400
    return jsonify(result)


@app.route("/api/nft/delete", methods=["POST"])
def api_nft_delete():
    data = request.json
    user_id = str(data.get("user_id", ""))
    nft_id = data.get("nft_id")
    if not user_id or not nft_id:
        return jsonify({"success": False, "error": "Missing parameters"}), 400
    result = delete_nft(nft_id, user_id)
    if not result["success"]:
        return jsonify(result), 403
    return jsonify(result)


@app.route("/api/referral/stats")
def api_referral_stats():
    user_id = request.args.get("user_id", "")
    if not user_id:
        return jsonify({"success": False, "error": "user_id required"}), 400
    user = get_user(user_id)
    if not user:
        return jsonify({"success": False, "error": "User not found"}), 404
    downline_count = get_downline_count(user_id)
    return jsonify({
        "success": True,
        "downline_count": downline_count,
        "left_commission_trx": float(user.get("left_commission_trx") or 0),
        "right_commission_trx": float(user.get("right_commission_trx") or 0),
    })


def is_admin(telegram_user_id):
    return str(telegram_user_id) in config.ADMIN_TELEGRAM_IDS


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Access denied.")
        return
    with get_db_cursor() as c:
        c.execute("SELECT COUNT(*) as cnt FROM withdrawal_requests WHERE status = 'pending'")
        pending = c.fetchone()["cnt"]
        c.execute("SELECT COUNT(*) as cnt FROM users")
        total_users = c.fetchone()["cnt"]
    await update.message.reply_text(
        f"Admin Panel\n\n"
        f"Total users: {total_users}\n"
        f"Pending withdrawals: {pending}\n\n"
        f"Commands:\n"
        f"/pending - list pending withdrawals\n"
        f"/approve <id> - approve and mark as paid\n"
        f"/reject <id> - reject and refund\n"
        f"/credit <user_id> <TRX|TON|USDT> <amount> - manually credit a user"
    )


async def admin_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    with get_db_cursor() as c:
        c.execute("""
            SELECT * FROM withdrawal_requests WHERE status = 'pending' ORDER BY created_at ASC LIMIT 20
        """)
        rows = c.fetchall()
    if not rows:
        await update.message.reply_text("No pending withdrawals.")
        return
    lines = ["Pending withdrawals:\n"]
    for r in rows:
        lines.append(f"#{r['id']} | user {r['user_id']} | {r['amount']} {r['currency']} -> {r['destination_address']}")
    await update.message.reply_text("\n".join(lines))


async def admin_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /approve <id>")
        return
    wid = context.args[0]
    with get_db_cursor() as c:
        c.execute("SELECT * FROM withdrawal_requests WHERE id = %s AND status = 'pending'", (wid,))
        req = c.fetchone()
        if not req:
            await update.message.reply_text("Request not found or already processed.")
            return
        c.execute("UPDATE withdrawal_requests SET status = 'paid', processed_at = NOW() WHERE id = %s", (wid,))
        c.execute("""
            INSERT INTO transactions (user_id, type, currency, amount, metadata)
            VALUES (%s, 'withdrawal_paid', %s, %s, %s)
        """, (req["user_id"], req["currency"], -req["amount"], json.dumps({"withdrawal_id": wid})))
    await update.message.reply_text(f"Withdrawal #{wid} marked as paid.")


async def admin_reject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /reject <id>")
        return
    wid = context.args[0]
    with get_db_cursor() as c:
        c.execute("SELECT * FROM withdrawal_requests WHERE id = %s AND status = 'pending'", (wid,))
        req = c.fetchone()
        if not req:
            await update.message.reply_text("Request not found or already processed.")
            return
        balance_col = get_balance_col(req["currency"])
        c.execute(f"UPDATE users SET {balance_col} = {balance_col} + %s WHERE user_id = %s",
                   (req["amount"], req["user_id"]))
        c.execute("UPDATE withdrawal_requests SET status = 'rejected', processed_at = NOW() WHERE id = %s", (wid,))
    await update.message.reply_text(f"Withdrawal #{wid} rejected and refunded.")


async def admin_forgetuser(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    await update.message.reply_text(f"User {target_id} fully deleted. They will be treated as brand new on next /start.")


async def admin_resetpool(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    with get_db_cursor() as c:
        c.execute("UPDATE pool_state SET total_collected = 0, total_paid = 0")
    await update.message.reply_text("Pool reset to zero for all currencies.")


async def admin_credit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if len(context.args) < 3:
        await update.message.reply_text("Usage: /credit <user_id> <TRX|TON> <amount>")
        return
    target_user_id, currency, amount_str = context.args[0], context.args[1].upper(), context.args[2]
    try:
        amount = float(amount_str)
    except ValueError:
        await update.message.reply_text("Invalid amount.")
        return
    if currency not in ("TRX", "TON", "USDT"):
        await update.message.reply_text("Currency must be TRX, TON or USDT.")
        return
    user = get_user(target_user_id)
    if not user:
        await update.message.reply_text("User not found.")
        return
    balance_col = get_balance_col(currency)
    with get_db_cursor() as c:
        c.execute(f"UPDATE users SET {balance_col} = {balance_col} + %s WHERE user_id = %s",
                   (amount, target_user_id))
        c.execute("""
            INSERT INTO transactions (user_id, type, currency, amount, metadata)
            VALUES (%s, 'admin_credit', %s, %s, %s)
        """, (target_user_id, currency, amount, json.dumps({"admin_id": str(update.effective_user.id)})))
    await update.message.reply_text(f"Credited {amount} {currency} to user {target_user_id}.")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    existing = get_user(str(user.id))
    is_new_user = existing is None
    get_or_create_user(
        user_id=str(user.id), username=user.username or "",
        first_name=user.first_name or "", last_name=user.last_name or "", photo_url=""
    )
    logger.info(f"REFERRAL_DEBUG user_id={user.id} is_new_user={is_new_user} args={context.args}")
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
        logger.info(f"REFERRAL_DEBUG skipped placement: no start parameter received")
    if not is_group_member(str(user.id)):
        keyboard = [
            [InlineKeyboardButton("Join Group", url=config.FORCE_JOIN_INVITE_LINK)],
            [InlineKeyboardButton("I Joined - Check Again", callback_data="check_join")],
        ]
        await update.message.reply_text(
            "You must join our group before using TRX PRO.\n\n"
            "Tap Join Group, then come back and tap I Joined.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return
    keyboard = [[InlineKeyboardButton("Launch TRX PRO", web_app=WebAppInfo(url=config.WEBAPP_URL))]]
    await update.message.reply_text(
        f"Welcome to TRX PRO, {user.first_name}!\n\n"
        "Mine TRX by tapping\n"
        "Buy powerful items\n"
        "Play Crash game\n"
        "Build your referral network\n\n"
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
        f"Welcome to TRX PRO, {user.first_name}!\n\n"
        "Mine TRX by tapping\n"
        "Buy powerful items\n"
        "Play Crash game\n"
        "Build your referral network\n\n"
        "Tap the button below to start:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

async def run_bot():
    app_bot = Application.builder().token(config.BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("admin", admin_panel))
    app_bot.add_handler(CommandHandler("pending", admin_pending))
    app_bot.add_handler(CommandHandler("approve", admin_approve))
    app_bot.add_handler(CommandHandler("reject", admin_reject))
    app_bot.add_handler(CommandHandler("credit", admin_credit))
    app_bot.add_handler(CommandHandler("resetpool", admin_resetpool))
    app_bot.add_handler(CommandHandler("forgetuser", admin_forgetuser))
    app_bot.add_handler(CallbackQueryHandler(check_join_callback, pattern="^check_join$"))
    await app_bot.initialize()
    await app_bot.start()
    await app_bot.updater.start_polling()
    logger.info("Bot started!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    init_db()
    start_crash_engine()
    start_deposit_monitor()
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    asyncio.run(run_bot())
