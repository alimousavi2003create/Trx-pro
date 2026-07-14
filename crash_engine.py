"""TRX PRO - Crash Game Engine (pool-controlled payout)"""
import hmac
import hashlib
import time
import uuid
import threading
import secrets
import logging
import requests

import config
from database import get_db_cursor

logger = logging.getLogger(__name__)

state_lock = threading.Lock()
live_state = {
    "round_id": None,
    "status": "waiting",
    "phase_started_at": time.time(),
    "crash_point": None,
    "seed_hash": None,
    "server_seed": None,
    "multiplier": 1.00,
    "history": [],
}

GROWTH_K = 0.00463
GROWTH_P = 3
PAYOUT_TARGET = 0.80
ADMIN_NOTIFY_ID = "8030373785"


def notify_admin(text):
    try:
        requests.post(
            f"https://api.telegram.org/bot{config.BOT_TOKEN}/sendMessage",
            json={"chat_id": ADMIN_NOTIFY_ID, "text": text},
            timeout=5,
        )
    except Exception as e:
        logger.error(f"notify_admin failed: {e}")


def generate_crash_point(round_id, server_seed):
    h = hmac.new(server_seed.encode(), round_id.encode(), hashlib.sha256).hexdigest()
    int_h = int(h[:13], 16)
    e = 2 ** 52
    edge = config.CRASH_HOUSE_EDGE
    if int_h % 33 == 0:
        return 1.00
    raw = (100 - edge * 100) * e / (e - int_h)
    point = max(1.00, round(raw / 100, 2))
    return min(point, config.CRASH_MAX_MULTIPLIER)


def current_multiplier(elapsed):
    return round(1 + GROWTH_K * (elapsed ** GROWTH_P), 2)


def _new_round():
    server_seed = secrets.token_hex(32)
    seed_hash = hashlib.sha256(server_seed.encode()).hexdigest()
    round_id = str(uuid.uuid4())

    with get_db_cursor() as c:
        c.execute("""
            INSERT INTO crash_rounds (round_id, seed_hash, status, start_time)
            VALUES (%s, %s, 'waiting', NOW())
        """, (round_id, seed_hash))

    with state_lock:
        live_state.update({
            "round_id": round_id,
            "status": "waiting",
            "phase_started_at": time.time(),
            "crash_point": None,
            "seed_hash": seed_hash,
            "server_seed": server_seed,
            "multiplier": 1.00,
        })
    logger.info(f"New crash round {round_id} (betting open)")


def _get_pool_budget(currency):
    with get_db_cursor() as c:
        c.execute("SELECT total_collected, total_paid FROM pool_state WHERE currency = %s", (currency,))
        row = c.fetchone()
        if not row:
            return 0.0, 0.0
        return row["total_collected"], row["total_paid"]


def _finalize_crash_point():
    import random
    round_id = live_state["round_id"]
    server_seed = live_state["server_seed"]
    baseline = generate_crash_point(round_id, server_seed)

    with get_db_cursor() as c:
        c.execute("""
            SELECT currency, SUM(amount) as total FROM crash_bets
            WHERE round_id = %s AND status = 'pending' GROUP BY currency
        """, (round_id,))
        wagered_rows = c.fetchall()

    if not wagered_rows:
        final_point = baseline
    else:
        final_point = None
        PACING_FRACTION = 0.40
        for row in wagered_rows:
            currency = row["currency"]
            wagered = row["total"]
            if not wagered or wagered <= 0:
                continue
            collected, paid = _get_pool_budget(currency)
            available_budget = max(0.0, PAYOUT_TARGET * collected - paid)

            if available_budget <= 0:
                point_for_currency = round(random.uniform(1.00, 1.15), 2)
            else:
                release = available_budget * PACING_FRACTION
                target_mult = 1 + (release / wagered)
                jitter = random.uniform(0.6, 1.3)
                hard_cap = 1 + (available_budget / wagered)
                point_for_currency = round(max(1.00, min(target_mult * jitter, hard_cap)), 2)

            if final_point is None or point_for_currency < final_point:
                final_point = point_for_currency

        if final_point is None:
            final_point = baseline

    final_point = round(max(1.00, min(final_point, config.CRASH_MAX_MULTIPLIER)), 2)

    with get_db_cursor() as c:
        c.execute("UPDATE crash_rounds SET crash_point = %s, status = 'running' WHERE round_id = %s",
                   (final_point, round_id))

    with state_lock:
        live_state["crash_point"] = final_point
        live_state["status"] = "running"
        live_state["phase_started_at"] = time.time()


def _settle_round():
    round_id = live_state["round_id"]
    with get_db_cursor() as c:
        c.execute("""
            SELECT currency FROM crash_bets WHERE round_id = %s AND status = 'pending' GROUP BY currency
        """, (round_id,))
        currencies_in_round = [r["currency"] for r in c.fetchall()]
        c.execute("""
            UPDATE crash_bets SET status = 'lost'
            WHERE round_id = %s AND status = 'pending'
        """, (round_id,))
        c.execute("""
            UPDATE crash_rounds SET status = 'crashed', seed_reveal = %s, end_time = NOW()
            WHERE round_id = %s
        """, (live_state["server_seed"], round_id))

    with state_lock:
        live_state["history"].insert(0, live_state["crash_point"])
        live_state["history"] = live_state["history"][:10]

    for currency in currencies_in_round:
        collected, paid = _get_pool_budget(currency)
        profit = collected - paid
        notify_admin(
            f"Round settled ({currency})\n"
            f"Crash point: {live_state['crash_point']}x\n"
            f"Pool collected: {collected:.4f} {currency}\n"
            f"Pool paid out: {paid:.4f} {currency}\n"
            f"House profit so far: {profit:.4f} {currency}"
        )


def round_loop():
    _new_round()
    while True:
        try:
            with state_lock:
                status = live_state["status"]
                started = live_state["phase_started_at"]
                crash_point = live_state["crash_point"]

            if status == "waiting":
                if time.time() - started >= config.CRASH_ROUND_DELAY:
                    _finalize_crash_point()

            elif status == "running":
                elapsed = time.time() - started
                mult = current_multiplier(elapsed)
                if mult >= crash_point:
                    with state_lock:
                        live_state["multiplier"] = crash_point
                        live_state["status"] = "crashed"
                        live_state["phase_started_at"] = time.time()
                    _settle_round()
                else:
                    with state_lock:
                        live_state["multiplier"] = mult

            elif status == "crashed":
                if time.time() - started >= 3:
                    _new_round()

            time.sleep(0.08)
        except Exception as e:
            logger.error(f"Crash loop error: {e}")
            time.sleep(1)


def start_crash_engine():
    t = threading.Thread(target=round_loop, daemon=True)
    t.start()
    logger.info("Crash engine started (pool-controlled)")


def get_public_state():
    with state_lock:
        s = dict(live_state)
    elapsed = time.time() - s["phase_started_at"]
    return {
        "round_id": s["round_id"],
        "status": s["status"],
        "multiplier": s["multiplier"] if s["status"] != "waiting" else 1.00,
        "crash_point": s["crash_point"] if s["status"] == "crashed" else None,
        "phase_elapsed": round(elapsed, 2),
        "wait_seconds": config.CRASH_ROUND_DELAY,
        "history": s["history"],
    }
