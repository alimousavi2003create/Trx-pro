# 2) frontend - show downline count + left/right commission
with open("templates/index.html", "r", encoding="utf-8") as f:
    content = f.read()

old_stats_block = '''        <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--glass-border);">
          <span style="font-size:13px;color:var(--text-muted);">Next Bonus</span>
          <span style="font-family:'Orbitron',sans-serif;font-size:14px;color:var(--neon-yellow);" id="nextBonusAmount">400 TRX</span>
        </div>
        <div style="display:flex;justify-content:space-between;padding:8px 0;">
          <span style="font-size:13px;color:var(--text-muted);">Bonus Cycles Earned</span>
          <span style="font-family:'Orbitron',sans-serif;font-size:14px;" id="cycleCount">0</span>
        </div>
      </div>
    </div>'''

new_stats_block = '''        <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--glass-border);">
          <span style="font-size:13px;color:var(--text-muted);">Next Bonus</span>
          <span style="font-family:'Orbitron',sans-serif;font-size:14px;color:var(--neon-yellow);" id="nextBonusAmount">400 TRX</span>
        </div>
        <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--glass-border);">
          <span style="font-size:13px;color:var(--text-muted);">Bonus Cycles Earned</span>
          <span style="font-family:'Orbitron',sans-serif;font-size:14px;" id="cycleCount">0</span>
        </div>
        <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--glass-border);">
          <span style="font-size:13px;color:var(--text-muted);">Total Downline</span>
          <span style="font-family:'Orbitron',sans-serif;font-size:14px;" id="downlineCount">0</span>
        </div>
        <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--glass-border);">
          <span style="font-size:13px;color:var(--text-muted);">Left Commission</span>
          <span style="font-family:'Orbitron',sans-serif;font-size:14px;color:var(--neon-cyan);" id="leftCommission">0 TRX</span>
        </div>
        <div style="display:flex;justify-content:space-between;padding:8px 0;">
          <span style="font-size:13px;color:var(--text-muted);">Right Commission</span>
          <span style="font-family:'Orbitron',sans-serif;font-size:14px;color:var(--neon-pink);" id="rightCommission">0 TRX</span>
        </div>
      </div>
    </div>'''
assert old_stats_block in content, "network-stats block anchor not found"
content = content.replace(old_stats_block, new_stats_block, 1)

old_hook = '''  if (tab === 'nft') { switchNftView('mint'); }'''
new_hook = '''  if (tab === 'nft') { switchNftView('mint'); }
  if (tab === 'referral') { loadReferralStats(); }'''
assert old_hook in content, "switchTab nft-hook anchor not found"
content = content.replace(old_hook, new_hook, 1)

old_tail = '''initAuth();
checkAdminStatus();
</script>'''
new_tail = '''async function loadReferralStats() {
  try {
    const r = await fetch(API_BASE + '/api/referral/stats?user_id=' + encodeURIComponent(userId));
    const d = await r.json();
    if (!d.success) return;
    document.getElementById('downlineCount').textContent = d.downline_count;
    document.getElementById('leftCommission').textContent = d.left_commission_trx.toFixed(2) + ' TRX';
    document.getElementById('rightCommission').textContent = d.right_commission_trx.toFixed(2) + ' TRX';
  } catch (e) {}
}

initAuth();
checkAdminStatus();
</script>'''
assert old_tail in content, "tail anchor not found"
content = content.replace(old_tail, new_tail, 1)

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(content)
print("index.html: downline count + left/right commission display added")
