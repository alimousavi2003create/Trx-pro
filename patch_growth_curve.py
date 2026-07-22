# 1) Server-side: crash_engine.py
with open("crash_engine.py", "r", encoding="utf-8") as f:
    content = f.read()

old_const_block = '''GROWTH_K = 0.05
GROWTH_P = 1.3
PAYOUT_TARGET = 0.80
GROUP_CHAT_ID = "-1003811791270"'''

new_const_block = '''GROWTH_K = 0.05
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


_BREAKPOINTS = _build_breakpoints()'''

assert old_const_block in content, "growth constants anchor not found"
content = content.replace(old_const_block, new_const_block, 1)

old_func = '''def current_multiplier(elapsed):
    return round(1 + GROWTH_K * (elapsed ** GROWTH_P), 2)'''

new_func = '''def current_multiplier(elapsed):
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
    return float(MULT_CAP)'''

assert old_func in content, "current_multiplier function anchor not found"
content = content.replace(old_func, new_func, 1)

with open("crash_engine.py", "w", encoding="utf-8") as f:
    f.write(content)
print("crash_engine.py: custom growth curve applied")
