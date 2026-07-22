with open("templates/index.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1) Add flight emoji element to the crash stage HTML
old_stage = '''      <div class="crash-stage">
        <canvas id="crashCanvas" class="crash-canvas"></canvas>
        <div class="crash-history" id="crashHistory">'''
new_stage = '''      <div class="crash-stage">
        <canvas id="crashCanvas" class="crash-canvas"></canvas>
        <div id="flightEmoji" style="position:absolute;left:50%;bottom:5%;transform:translateX(-50%);font-size:32px;transition:bottom 0.3s linear;z-index:5;">\\U0001F969</div>
        <div class="crash-history" id="crashHistory">'''
assert old_stage in content, "crash-stage anchor not found"
content = content.replace(old_stage, new_stage, 1)

# 2) Mirror growth curve constants + breakpoints, add computeMultiplier()
old_consts = '''const CRASH_GROWTH_K = 0.05;
const CRASH_GROWTH_P = 1.3;'''
new_consts = '''const CRASH_GROWTH_K = 0.05;
const CRASH_GROWTH_P = 1.3;
const STEP_DURATIONS = {5: 3.0, 6: 2.0, 7: 1.5, 8: 1.0, 9: 1.0};
const DEFAULT_STEP_DURATION = 1.0;
const MULT_CAP = 30;
const CRASH_T5 = Math.pow((5 - 1) / CRASH_GROWTH_K, 1 / CRASH_GROWTH_P);
const CRASH_BREAKPOINTS = (function() {
  const pts = [[5, CRASH_T5]];
  let t = CRASH_T5, m = 5;
  while (m < MULT_CAP) {
    const dur = STEP_DURATIONS[m] !== undefined ? STEP_DURATIONS[m] : DEFAULT_STEP_DURATION;
    t += dur; m += 1;
    pts.push([m, t]);
  }
  return pts;
})();

function computeMultiplier(elapsed) {
  if (elapsed <= 0) return 1.0;
  if (elapsed <= CRASH_T5) return 1 + CRASH_GROWTH_K * Math.pow(elapsed, CRASH_GROWTH_P);
  for (let i = 0; i < CRASH_BREAKPOINTS.length - 1; i++) {
    const m0 = CRASH_BREAKPOINTS[i][0], t0 = CRASH_BREAKPOINTS[i][1];
    const m1 = CRASH_BREAKPOINTS[i + 1][0], t1 = CRASH_BREAKPOINTS[i + 1][1];
    if (elapsed <= t1) {
      const frac = (elapsed - t0) / (t1 - t0);
      return m0 + frac * (m1 - m0);
    }
  }
  return MULT_CAP;
}'''
assert old_consts in content, "CRASH_GROWTH constants anchor not found"
content = content.replace(old_consts, new_consts, 1)

# 3) Use computeMultiplier() in tickMultiplier + update flight emoji position
old_tick_mult = '''  const mult = 1 + CRASH_GROWTH_K * Math.pow(estElapsed, CRASH_GROWTH_P);
  const multNumEl = document.getElementById('multNum');
  if (multNumEl) multNumEl.textContent = mult.toFixed(2) + 'x';'''
new_tick_mult = '''  const mult = computeMultiplier(estElapsed);
  const multNumEl = document.getElementById('multNum');
  if (multNumEl) multNumEl.textContent = mult.toFixed(2) + 'x';
  const flightEl = document.getElementById('flightEmoji');
  if (flightEl) {
    const progress = Math.min(1, (mult - 1) / 9);
    flightEl.style.bottom = (5 + progress * 80) + '%';
  }'''
assert old_tick_mult in content, "tickMultiplier mult calc anchor not found"
content = content.replace(old_tick_mult, new_tick_mult, 1)

# 4) Reset emoji to steak on waiting, switch to eggplant on crash
old_waiting = '''      multNum.textContent = '1.00x';
      multLabel.textContent = `STARTING IN ${left}s`;'''
new_waiting = '''      multNum.textContent = '1.00x';
      multLabel.textContent = `STARTING IN ${left}s`;
      const flightElW = document.getElementById('flightEmoji');
      if (flightElW) { flightElW.textContent = '\\U0001F969'; flightElW.style.bottom = '5%'; }'''
assert old_waiting in content, "waiting-state anchor not found"
content = content.replace(old_waiting, new_waiting, 1)

old_crashed = '''      multNum.textContent = d.crash_point.toFixed(2) + 'x';
      multLabel.textContent = 'CRASHED';'''
new_crashed = '''      multNum.textContent = d.crash_point.toFixed(2) + 'x';
      multLabel.textContent = 'CRASHED';
      const flightElC = document.getElementById('flightEmoji');
      if (flightElC) { flightElC.textContent = '\\U0001F346'; }'''
assert old_crashed in content, "crashed-state anchor not found"
content = content.replace(old_crashed, new_crashed, 1)

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(content)
print("index.html: growth curve mirrored + flying emoji (steak to eggplant) added")
