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
from telegram.ext import Application, CommandHandler, ContextTypes

import config
from database import init_db, get_db_cursor
from auth import verify_init_data
from models import get_or_create_user, get_user, update_balance, get_inventory, get_transactions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("index.html")

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
    return jsonify({
        "success": True,
        "user": {
            "user_id": user["user_id"], "username": user["username"],
            "first_name": user["first_name"], "balance_trx": user["balance_trx"],
            "balance_ton": user["balance_ton"], "mining_power": user["mining_power"],
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
            "balance_ton": user["balance_ton"], "mining_power": user["mining_power"],
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
        balance_col = "balance_trx" if currency == "TRX" else "balance_ton"
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
        ("auto_miner_v1", "Auto Miner v1", "Auto-mine 0.5 TRX per hour",
         "auto_mine", 0.5, 500, None, 30, "Rare"),
        ("energy_core_v1", "Energy Core", "+50 Max Energy",
         "energy", 50, 200, None, 0, "Common"),
        ("trx_booster_v1", "TRX Booster", "+1.0 Mining Power",
         "mining_speed", 1.0, 300, None, 7, "Rare"),
        ("ultra_miner_v1", "Ultra Miner", "Auto-mine 2.0 TRX per hour",
         "auto_mine", 2.0, 1500, 0.5, 30, "Epic"),
        ("legendary_core", "Legendary Core", "+200 Max Energy & +2.0 Mining Power",
         "energy", 200, 3000, 2.0, 0, "Legendary"),
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db_user = get_or_create_user(
        user_id=str(user.id), username=user.username or "",
        first_name=user.first_name or "", last_name=user.last_name or "", photo_url=""
    )
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

def run_flask():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

async def run_bot():
    app_bot = Application.builder().token(config.BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    await app_bot.initialize()
    await app_bot.start()
    await app_bot.updater.start_polling()
    logger.info("Bot started!")
    await asyncio.Event().wait()

if __name__ == "__main__":
    init_db()
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    asyncio.run(run_bot())
