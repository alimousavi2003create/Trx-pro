with open("templates/index.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1) Fix shareRef() - config.WEBAPP_URL doesn't exist in JS scope. Use a proper deep link with bot username.
old_share = '''function shareRef() {
  const code = userData.referral_code || '';
  const text = `Join TRX PRO and start mining! Use my code: ${code}`;
  if (tg) tg.openTelegramLink(`https://t.me/share/url?url=${encodeURIComponent(config.WEBAPP_URL)}&text=${encodeURIComponent(text)}`);
}'''
new_share = '''function shareRef() {
  const code = userData.referral_code || '';
  const botUsername = window.__BOT_USERNAME__ || '';
  const deepLink = botUsername ? `https://t.me/${botUsername}?start=${encodeURIComponent(code)}` : '';
  const text = `Join TRX PRO and start mining! Use my code: ${code}`;
  if (tg && deepLink) {
    tg.openTelegramLink(`https://t.me/share/url?url=${encodeURIComponent(deepLink)}&text=${encodeURIComponent(text)}`);
  } else if (deepLink) {
    navigator.clipboard.writeText(deepLink).then(() => showToast('Referral link copied!', 'success'));
  } else {
    showToast('Referral link unavailable', 'error');
  }
}'''
assert old_share in content, "shareRef anchor not found"
content = content.replace(old_share, new_share, 1)

# 2) Inject bot username as a global JS var (set from Flask template) right before API_BASE line
old_apibase = "const API_BASE = '';"
new_apibase = "const API_BASE = '';\nwindow.__BOT_USERNAME__ = '{{ bot_username }}';"
assert old_apibase in content, "API_BASE anchor not found"
content = content.replace(old_apibase, new_apibase, 1)

# 3) Show cycle_count (binary bonus cycles earned) in referral tab, under Network Stats
old_stats_block = '''        <div style="display:flex;justify-content:space-between;padding:8px 0;">
          <span style="font-size:13px;color:var(--text-muted);">Next Bonus</span>
          <span style="font-family:'Orbitron',sans-serif;font-size:14px;color:var(--neon-yellow);">400 TRX</span>
        </div>
      </div>
    </div>

    <!-- TAB: Profile -->'''
new_stats_block = '''        <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--glass-border);">
          <span style="font-size:13px;color:var(--text-muted);">Next Bonus</span>
          <span style="font-family:'Orbitron',sans-serif;font-size:14px;color:var(--neon-yellow);" id="nextBonusAmount">400 TRX</span>
        </div>
        <div style="display:flex;justify-content:space-between;padding:8px 0;">
          <span style="font-size:13px;color:var(--text-muted);">Bonus Cycles Earned</span>
          <span style="font-family:'Orbitron',sans-serif;font-size:14px;" id="cycleCount">0</span>
        </div>
      </div>
    </div>

    <!-- TAB: Profile -->'''
assert old_stats_block in content, "network-stats anchor not found"
content = content.replace(old_stats_block, new_stats_block, 1)

# 4) Update updateUI() to populate left/right volumes and cycle count from userData
old_updateui_end = '''  if (photoUrl) document.getElementById('profileAvatar').innerHTML = `<img src="${photoUrl}" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">`;
}'''
new_updateui_end = '''  if (photoUrl) document.getElementById('profileAvatar').innerHTML = `<img src="${photoUrl}" style="width:100%;height:100%;border-radius:50%;object-fit:cover;">`;

  const leftVol = userData.left_volume || 0;
  const rightVol = userData.right_volume || 0;
  const maxVol = Math.max(leftVol, rightVol, 1);
  document.getElementById('leftVol').textContent = leftVol.toFixed(2) + ' TRX';
  document.getElementById('rightVol').textContent = rightVol.toFixed(2) + ' TRX';
  document.getElementById('leftFill').style.width = Math.min(100, (leftVol / maxVol) * 100) + '%';
  document.getElementById('rightFill').style.width = Math.min(100, (rightVol / maxVol) * 100) + '%';
  document.getElementById('netLeft').textContent = leftVol.toFixed(2) + ' TRX';
  document.getElementById('netRight').textContent = rightVol.toFixed(2) + ' TRX';
  document.getElementById('cycleCount').textContent = userData.cycle_count || 0;
}'''
assert old_updateui_end in content, "updateUI-end anchor not found"
content = content.replace(old_updateui_end, new_updateui_end, 1)

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("index.html referral frontend patch applied successfully")
