"""TRX PRO - Crash Game Engine"""
import hmac
import hashlib
import time
import uuid
import threading
import secrets
import logging

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

GROWTH_RATE = 0.25


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
    K = 0.09
    P = 1.35
    return round(1 + K * (elapsed ** P), 2)


def _new_round():
    server_seed = secrets.token_hex(32)
    seed_hash = hashlib.sha256(server_seed.encode()).hexdigest()
    round_id = str(uuid.uuid4())
    crash_point = generate_crash_point(round_id, server_seed)

    with get_db_cursor() as c:
        c.execute("""
            INSERT INTO crash_rounds (round_id, seed_hash, crash_point, status, start_time)
            VALUES (%s, %s, %s, 'waiting', NOW())
        """, (round_id, seed_hash, crash_point))

    with state_lock:
        live_state.update({
            "round_id": round_id,
            "status": "waiting",
            "phase_started_at": time.time(),
            "crash_point": crash_point,
            "seed_hash": seed_hash,
            "server_seed": server_seed,
            "multiplier": 1.00,
        })
    logger.info(f"New crash round {round_id} (hidden crash={crash_point})")


def _settle_round():
    round_id = live_state["round_id"]
    with get_db_cursor() as c:
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
                    with get_db_cursor() as c:
                        c.execute("""
                            UPDATE crash_rounds SET status = 'running' WHERE round_id = %s
                        """, (live_state["round_id"],))
                    with state_lock:
                        live_state["status"] = "running"
                        live_state["phase_started_at"] = time.time()

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
    logger.info("Crash engine started")


def get_public_state():
    with state_lock:
        s = dict(live_state)
    elapsed = time.time() - s["phase_started_at"]
    return {
        "round_id": s["round_id"],
        "status": s["status"],
        "multiplier": s["multiplier"] if s["status"] != "waiting" else 1.00,
        "seed_hash": s["seed_hash"],
        "seed_reveal": s["server_seed"] if s["status"] == "crashed" else None,
        "crash_point": s["crash_point"] if s["status"] == "crashed" else None,
        "phase_elapsed": round(elapsed, 2),
        "wait_seconds": config.CRASH_ROUND_DELAY,
        "history": s["history"],
    }
