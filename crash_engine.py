"""TRX PRO - Crash Game Engine (pool-controlled payout)"""
import hmac
import hashlib
import time
import uuid
import threading
import secrets
import logging
import requests
import random

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

GROWTH_K = 0.05
GROWTH_P = 1.3
PAYOUT_TARGET = 0.80
GROUP_CHAT_ID = "-1003811791270"

STEP_DURATIONS = {5: 3.0, 6: 2.0, 7: 1.5, 8: 1.0, 9: 1.0}
DEFAULT_STEP_DURATION = 1.0
MULT_CAP = 30


def _time_at_mult(m):
    return ((m - 1) / GROWTH_K) ** (1 / GROWTH_P)


_T5 = _time_at_mult(5)


def _build_breakpoints():
    points = [(5, _T5)]
    t = _T5
    m = 5
    while m < MULT_CAP:
        dur = STEP_DURATIONS.get(m, DEFAULT_STEP_DURATION)
        t += dur
        m += 1
        points.append((m, t))
    return points


_BREAKPOINTS = _build_breakpoints()


def notify_group(text, sticker_id=None, reply_markup=None, parse_mode=None):
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
    if elapsed <= 0:
        return 1.0
    if elapsed <= _T5:
        return round(1 + GROWTH_K * (elapsed ** GROWTH_P), 2)
    for i in range(len(_BREAKPOINTS) - 1):
        m0, t0 = _BREAKPOINTS[i]
        m1, t1 = _BREAKPOINTS[i + 1]
        if elapsed <= t1:
            frac = (elapsed - t0) / (t1 - t0)
            return round(m0 + frac * (m1 - m0), 2)
    return float(MULT_CAP)


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
        PACING_FRACTION = 0.75
        for row in wagered_rows:
            currency = row["currency"]
            wagered = row["total"]
            if not wagered or wagered <= 0:
                continue
            collected, paid = _get_pool_budget(currency)
            net_reserve = max(0.0, collected - paid)
            safety_margin = 0.5
            available_budget = max(0.0, PAYOUT_TARGET * collected - paid)
            safe_cap_budget = net_reserve * safety_margin

            if safe_cap_budget <= 0:
                point_for_currency = round(random.uniform(1.00, 1.15), 2)
            else:
                release = min(available_budget, safe_cap_budget) * PACING_FRACTION
                target_mult = 1 + (release / wagered)
                jitter = random.uniform(0.6, 1.3)
                hard_cap = 1 + (safe_cap_budget / wagered)
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


ROUND_MESSAGE_TEMPLATES = [
'&● ROUND CLOSED ◇&\n{color} Multiplier: {mult}x\n&&& @Minerbyner_bot ●●●',
'◇》 ROUND CLOSED ~£\n{color} Multiplier: {mult}x\n○○○ @Minerbyner_bot ●●●',
'●○ ROUND CLOSED 《》\n{color} Multiplier: {mult}x\n<<< @Minerbyner_bot ○○○',
':◇♤ TRX PRO 》•,\n{color} Closed at {mult}x\nJoin: @Minerbyner_bot -',
'+○》 TRX PRO 《$/\n{color} Closed at {mult}x\nJoin: @Minerbyner_bot ÷',
'Round settled ,,\n{color} {mult}x\n《 TRX PRO - @Minerbyner_bot',
'◇<& TRX PRO -●<\n{color} Closed at {mult}x\nJoin: @Minerbyner_bot &',
'♤< ROUND CLOSED ☆-\n{color} Multiplier: {mult}x\n,,, @Minerbyner_bot &&&',
'Round settled $¡\n{color} {mult}x\n! TRX PRO + @Minerbyner_bot',
'》< ROUND CLOSED ¡+\n{color} Multiplier: {mult}x\n--- @Minerbyner_bot ■■■',
'Round settled <●\n{color} {mult}x\n¡ TRX PRO ● @Minerbyner_bot',
': CRASH RESULT ♤\n{mult}x {color}\n<< Play now ~~ @Minerbyner_bot',
'<●$ TRX PRO ,/!\n{color} Closed at {mult}x\nJoin: @Minerbyner_bot ¡',
'<《 ROUND CLOSED ♤○\n{color} Multiplier: {mult}x\n~~~ @Minerbyner_bot ÷÷÷',
'◇- ROUND CLOSED ◇-\n{color} Multiplier: {mult}x\n]]] @Minerbyner_bot ■■■',
',÷! TRX PRO □,☆\n{color} Closed at {mult}x\nJoin: @Minerbyner_bot ~',
'》]& TRX PRO ÷•♤\n{color} Closed at {mult}x\nJoin: @Minerbyner_bot -',
'Round settled ]]\n{color} {mult}x\n, TRX PRO - @Minerbyner_bot',
'Round settled 《》\n{color} {mult}x\n] TRX PRO / @Minerbyner_bot',
'£ CRASH RESULT /\n{mult}x {color}\n《《 Play now ○○ @Minerbyner_bot',
'□] ROUND CLOSED ÷♤\n{color} Multiplier: {mult}x\n!!! @Minerbyner_bot ☆☆☆',
'》 CRASH RESULT ●\n{mult}x {color}\n□□ Play now ~~ @Minerbyner_bot',
'&■ ROUND CLOSED ,-\n{color} Multiplier: {mult}x\n--- @Minerbyner_bot <<<',
'○ CRASH RESULT &\n{mult}x {color}\n◇◇ Play now ☆☆ @Minerbyner_bot',
'< CRASH RESULT ¡\n{mult}x {color}\n》》 Play now ◇◇ @Minerbyner_bot',
'♤》, TRX PRO ~]&\n{color} Closed at {mult}x\nJoin: @Minerbyner_bot ¡',
'+&◇ TRX PRO ♤!!\n{color} Closed at {mult}x\nJoin: @Minerbyner_bot ~',
'《《《《\n{color} {mult}x ,\n<<<<\n@Minerbyner_bot',
'Round settled <$\n{color} {mult}x\n♤ TRX PRO ! @Minerbyner_bot',
'£ CRASH RESULT 《\n{mult}x {color}\n》》 Play now ~~ @Minerbyner_bot',
'-□》 TRX PRO □-+\n{color} Closed at {mult}x\nJoin: @Minerbyner_bot 《',
'《~ ROUND CLOSED ○◇\n{color} Multiplier: {mult}x\n]]] @Minerbyner_bot £££',
']◇ ROUND CLOSED <!\n{color} Multiplier: {mult}x\n,,, @Minerbyner_bot ■■■',
'~♤• TRX PRO $○-\n{color} Closed at {mult}x\nJoin: @Minerbyner_bot 《',
'Round settled ♤<\n{color} {mult}x\n• TRX PRO ¡ @Minerbyner_bot',
'■£ ROUND CLOSED !£\n{color} Multiplier: {mult}x\n/// @Minerbyner_bot ●●●',
'◇☆< TRX PRO &+•\n{color} Closed at {mult}x\nJoin: @Minerbyner_bot ♤',
'◇&■ TRX PRO 》••\n{color} Closed at {mult}x\nJoin: @Minerbyner_bot ◇',
'Round settled ○》\n{color} {mult}x\n] TRX PRO £ @Minerbyner_bot',
'□$☆ TRX PRO ~•+\n{color} Closed at {mult}x\nJoin: @Minerbyner_bot £',
'~~~~\n{color} {mult}x ]\n!!!!\n@Minerbyner_bot',
'Round settled :/\n{color} {mult}x\n$ TRX PRO ◇ @Minerbyner_bot',
'■ CRASH RESULT :\n{mult}x {color}\n-- Play now // @Minerbyner_bot',
'Round settled 》!\n{color} {mult}x\n& TRX PRO ÷ @Minerbyner_bot',
'♤○ ROUND CLOSED -》\n{color} Multiplier: {mult}x\n÷÷÷ @Minerbyner_bot ♤♤♤',
'☆◇ ROUND CLOSED ☆<\n{color} Multiplier: {mult}x\n~~~ @Minerbyner_bot &&&',
'■ CRASH RESULT 《\n{mult}x {color}\n♤♤ Play now ◇◇ @Minerbyner_bot',
'《 CRASH RESULT ]\n{mult}x {color}\n☆☆ Play now ,, @Minerbyner_bot',
'••••\n{color} {mult}x ■\n■■■■\n@Minerbyner_bot',
'》 CRASH RESULT +\n{mult}x {color}\n~~ Play now ◇◇ @Minerbyner_bot',
'Round settled :<\n{color} {mult}x\n/ TRX PRO ] @Minerbyner_bot',
'《《《《\n{color} {mult}x ¡\n○○○○\n@Minerbyner_bot',
'] CRASH RESULT +\n{mult}x {color}\n□□ Play now □□ @Minerbyner_bot',
'/♤• TRX PRO £♤]\n{color} Closed at {mult}x\nJoin: @Minerbyner_bot ○',
'£◇ ROUND CLOSED ¡/\n{color} Multiplier: {mult}x\n/// @Minerbyner_bot ]]]',
'Round settled ÷•\n{color} {mult}x\n- TRX PRO / @Minerbyner_bot',
'Round settled •○\n{color} {mult}x\n, TRX PRO : @Minerbyner_bot',
'Round settled --\n{color} {mult}x\n÷ TRX PRO / @Minerbyner_bot',
'Round settled &¡\n{color} {mult}x\n< TRX PRO & @Minerbyner_bot',
'• CRASH RESULT ]\n{mult}x {color}\n》》 Play now ~~ @Minerbyner_bot',
'/:■ TRX PRO &♤□\n{color} Closed at {mult}x\nJoin: @Minerbyner_bot ◇',
'Round settled -<\n{color} {mult}x\n, TRX PRO □ @Minerbyner_bot',
'Round settled ◇》\n{color} {mult}x\n■ TRX PRO • @Minerbyner_bot',
'::::\n{color} {mult}x /\n◇◇◇◇\n@Minerbyner_bot',
'•]- TRX PRO ÷■÷\n{color} Closed at {mult}x\nJoin: @Minerbyner_bot !',
'$/》 TRX PRO ♤~/\n{color} Closed at {mult}x\nJoin: @Minerbyner_bot 《',
'■■■■\n{color} {mult}x !\n••••\n@Minerbyner_bot',
'Round settled ]》\n{color} {mult}x\n- TRX PRO □ @Minerbyner_bot',
'~~~~\n{color} {mult}x •\n----\n@Minerbyner_bot',
'-♤ ROUND CLOSED ◇<\n{color} Multiplier: {mult}x\n::: @Minerbyner_bot 》》》',
'+ CRASH RESULT ]\n{mult}x {color}\n◇◇ Play now ♤♤ @Minerbyner_bot',
'□□□□\n{color} {mult}x £\n◇◇◇◇\n@Minerbyner_bot',
'Round settled <■\n{color} {mult}x\n- TRX PRO ● @Minerbyner_bot',
'÷,: TRX PRO $-♤\n{color} Closed at {mult}x\nJoin: @Minerbyner_bot ]',
'Round settled ●<\n{color} {mult}x\n◇ TRX PRO ] @Minerbyner_bot',
'/■》 TRX PRO ♤○■\n{color} Closed at {mult}x\nJoin: @Minerbyner_bot •',
'Round settled &◇\n{color} {mult}x\n: TRX PRO 《 @Minerbyner_bot',
',]< TRX PRO :□£\n{color} Closed at {mult}x\nJoin: @Minerbyner_bot ☆',
',♤ ROUND CLOSED 》:\n{color} Multiplier: {mult}x\n+++ @Minerbyner_bot ~~~',
'----\n{color} {mult}x -\n¡¡¡¡\n@Minerbyner_bot',
'----\n{color} {mult}x ●\n----\n@Minerbyner_bot',
'《》○ TRX PRO ]《÷\n{color} Closed at {mult}x\nJoin: @Minerbyner_bot <',
'♤■ ROUND CLOSED /:\n{color} Multiplier: {mult}x\n::: @Minerbyner_bot $$$',
'Round settled 《◇\n{color} {mult}x\n• TRX PRO : @Minerbyner_bot',
'-》 ROUND CLOSED 》$\n{color} Multiplier: {mult}x\n♤♤♤ @Minerbyner_bot £££',
'☆]/ TRX PRO ●</\n{color} Closed at {mult}x\nJoin: @Minerbyner_bot ■',
'Round settled :]\n{color} {mult}x\n] TRX PRO ! @Minerbyner_bot',
'&&&&\n{color} {mult}x ☆\n¡¡¡¡\n@Minerbyner_bot',
'●●●●\n{color} {mult}x <\n££££\n@Minerbyner_bot',
'○¡ ROUND CLOSED ■]\n{color} Multiplier: {mult}x\n<<< @Minerbyner_bot $$$',
'Round settled ☆•\n{color} {mult}x\n~ TRX PRO : @Minerbyner_bot',
',♤& TRX PRO ●]-\n{color} Closed at {mult}x\nJoin: @Minerbyner_bot ○',
'Round settled ]》\n{color} {mult}x\n/ TRX PRO & @Minerbyner_bot',
'Round settled ~/\n{color} {mult}x\n÷ TRX PRO 《 @Minerbyner_bot',
'《 CRASH RESULT <\n{mult}x {color}\n•• Play now -- @Minerbyner_bot',
'☆<• TRX PRO ,●~\n{color} Closed at {mult}x\nJoin: @Minerbyner_bot !',
'Round settled □☆\n{color} {mult}x\n$ TRX PRO ◇ @Minerbyner_bot',
'■ CRASH RESULT &\n{mult}x {color}\n&& Play now $$ @Minerbyner_bot',
'::::\n{color} {mult}x ¡\n////\n@Minerbyner_bot',
'&○ ROUND CLOSED :]\n{color} Multiplier: {mult}x\n£££ @Minerbyner_bot £££',
]


CELEBRATION_EMOJIS = [
    "\U0001F96D", "\U0001F34D", "\U0001F34C", "\U0001F34B", "\U0001F34A", "\U0001F349",
    "\U0001F348", "\U0001F347", "\U0001F95D", "\U0001FAD0", "\U0001F353", "\U0001F352",
    "\U0001F351", "\U0001F350", "\U0001F34F", "\U0001F34E", "\U0001F345", "\U0001FAD2",
    "\U0001F965", "\U0001F951", "\U0001F346", "\U0001F954", "\U0001F955", "\U0001F9C5",
    "\U0001F9C4", "\U0001F966", "\U0001F96C", "\U0001F952", "\U0001F336", "\U0001F33D",
    "\U0001FAD1", "\U0001FAD8", "\U0001F95C", "\U0001F35E", "\U0001F950", "\U0001F956",
    "\U0001FAD3", "\U0001F330", "\U0001FADA", "\U0001F968", "\U0001F96F", "\U0001F9C7",
    "\U0001F9C0", "\U0001F355", "\U0001F35F", "\U0001F354", "\U0001F953", "\U0001F969",
    "\U0001F357", "\U0001F32D", "\U0001F96A", "\U0001F32E", "\U0001F32F",
    "\U0001F95E", "\U0001F366", "\U0001F9C1", "\U0001F36C", "\U0001F36A",
    "\U0001F36E", "\U0001F37B", "\U0001F964", "\U0001F9C3", "\U0001F379", "\U0001F370",
    "\U0001F3FA", "\U0001F9CA", "\U0001F374", "\U0001F37D",
    "\U0001F37E", "\U0001F376",
]


def _settle_round():
    round_id = live_state["round_id"]
    cp = live_state["crash_point"]
    if cp and cp > 10:
        emoji = random.choice(CELEBRATION_EMOJIS)
        celebration_text = (
            f"{emoji} <b>{cp}x!</b>\n"
            f"Someone just hit a huge multiplier in TRX PRO Crash!"
        )
        keyboard = {
            "inline_keyboard": [[
                {"text": "\U0001F680 Play Now", "url": "https://t.me/Minerbyner_bot?start=celebration"}
            ]]
        }
        notify_group(celebration_text, reply_markup=keyboard, parse_mode="HTML")
    with get_db_cursor() as c:
        c.execute("""
            SELECT currency, COUNT(*) as cnt, SUM(amount) as total
            FROM crash_bets WHERE round_id = %s AND status = 'pending' GROUP BY currency
        """, (round_id,))
        lost_rows = c.fetchall()
        c.execute("""
            SELECT user_id, currency, amount FROM crash_bets
            WHERE round_id = %s AND status = 'pending'
        """, (round_id,))
        individual_losers = c.fetchall()
        c.execute("""
            UPDATE crash_bets SET status = 'lost'
            WHERE round_id = %s AND status = 'pending'
        """, (round_id,))
        c.execute("""
            UPDATE crash_rounds SET status = 'crashed', seed_reveal = %s, end_time = NOW()
            WHERE round_id = %s
        """, (live_state["server_seed"], round_id))

    from models import pay_direct_referral_bonus
    for loser in individual_losers:
        try:
            pay_direct_referral_bonus(loser["user_id"], loser["currency"], float(loser["amount"]), "loss")
        except Exception as e:
            logger.error(f"crash loss referral bonus failed: {e}")

    with state_lock:
        live_state["history"].insert(0, live_state["crash_point"])
        live_state["history"] = live_state["history"][:10]

    # loss notifications removed to reduce group clutter (per request)


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
