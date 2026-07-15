with open("templates/index.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1) Add a full-link display box under the code
old_box = '''      <div class="referral-code-box">
        <div style="font-size:11px;color:var(--text-muted);margin-bottom:8px;text-transform:uppercase;letter-spacing:1px;">Your Referral Code</div>
        <div class="ref-code" id="refCode">TRX_------</div>
        <div class="ref-buttons">
          <button class="ref-btn" onclick="copyRefCode()">📋 Copy</button>
          <button class="ref-btn" onclick="shareRef()">📤 Share</button>
        </div>
      </div>'''
new_box = '''      <div class="referral-code-box">
        <div style="font-size:11px;color:var(--text-muted);margin-bottom:8px;text-transform:uppercase;letter-spacing:1px;">Your Referral Code</div>
        <div class="ref-code" id="refCode">TRX_------</div>
        <div style="font-size:11px;color:var(--neon-cyan);word-break:break-all;margin-bottom:12px;padding:8px;background:rgba(255,255,255,0.04);border-radius:8px;" id="refLinkDisplay">Link unavailable</div>
        <div class="ref-buttons">
          <button class="ref-btn" onclick="copyRefCode()">📋 Copy Link</button>
          <button class="ref-btn" onclick="shareRef()">📤 Share</button>
        </div>
      </div>'''
assert old_box in content, "referral-code-box anchor not found"
content = content.replace(old_box, new_box, 1)

# 2) Add helper to build the link, use it in updateUI, fix copyRefCode
old_update_end = '''  document.getElementById('refCode').textContent = userData.referral_code || 'TRX_------';'''
new_update_end = '''  document.getElementById('refCode').textContent = userData.referral_code || 'TRX_------';
  document.getElementById('refLinkDisplay').textContent = getReferralLink();'''
assert old_update_end in content, "refCode line anchor not found"
content = content.replace(old_update_end, new_update_end, 1)

old_copy_share = '''function copyRefCode() {
  const code = document.getElementById('refCode').textContent;
  navigator.clipboard.writeText(code).then(() => showToast('Code copied!', 'success'));
}

function shareRef() {
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
new_copy_share = '''function getReferralLink() {
  const code = userData.referral_code || '';
  const botUsername = window.__BOT_USERNAME__ || '';
  if (!code || !botUsername) return 'Link unavailable';
  return `https://t.me/${botUsername}?start=${encodeURIComponent(code)}`;
}

function copyRefCode() {
  const link = getReferralLink();
  if (link === 'Link unavailable') { showToast('Referral link not ready yet', 'error'); return; }
  navigator.clipboard.writeText(link).then(() => showToast('Referral link copied!', 'success'));
}

function shareRef() {
  const code = userData.referral_code || '';
  const deepLink = getReferralLink();
  const text = `Join TRX PRO and start mining! Use my code: ${code}`;
  if (deepLink === 'Link unavailable') { showToast('Referral link not ready yet', 'error'); return; }
  if (tg) {
    tg.openTelegramLink(`https://t.me/share/url?url=${encodeURIComponent(deepLink)}&text=${encodeURIComponent(text)}`);
  } else {
    navigator.clipboard.writeText(deepLink).then(() => showToast('Referral link copied!', 'success'));
  }
}'''
assert old_copy_share in content, "copyRefCode/shareRef anchor not found"
content = content.replace(old_copy_share, new_copy_share, 1)

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("index.html referral-link fix applied successfully")
