with open("templates/index.html", "r", encoding="utf-8") as f:
    content = f.read()

old_tree = '''      <div class="tree-visual">
        <div class="tree-node">👤</div>
        <div style="font-size:14px;font-weight:700;">You</div>
        <div class="tree-branches">
          <div class="tree-leg leg-left">
            <div style="font-size:12px;color:var(--neon-cyan);font-weight:700;">LEFT</div>
            <div class="leg-bar"><div class="leg-fill" id="leftFill" style="width:0%"></div></div>
            <div style="font-size:11px;color:var(--text-muted);" id="leftVol">0 TRX</div>
          </div>
          <div class="tree-leg leg-right">
            <div style="font-size:12px;color:var(--neon-pink);font-weight:700;">RIGHT</div>
            <div class="leg-bar"><div class="leg-fill" id="rightFill" style="width:0%"></div></div>
            <div style="font-size:11px;color:var(--text-muted);" id="rightVol">0 TRX</div>
          </div>
        </div>
      </div>'''
assert old_tree in content, "tree-visual anchor not found"
new_tree = '''      <div class="tree-visual">
        <div class="tree-node">👤</div>
        <div style="font-size:14px;font-weight:700;">You</div>
        <div class="tree-branches">
          <div class="tree-leg leg-left">
            <div style="font-size:12px;color:var(--neon-cyan);font-weight:700;">LEFT</div>
            <div class="leg-bar"><div class="leg-fill" id="leftFill" style="width:0%"></div></div>
            <div style="font-size:11px;color:var(--text-muted);" id="leftVol">0 TRX</div>
            <div style="font-size:11px;color:var(--text-muted);margin-top:6px;"><span id="leftDownlineCount">0</span> نفر</div>
            <div style="font-size:12px;color:var(--neon-cyan);font-weight:700;margin-top:2px;" id="leftCommission">0 TRX</div>
          </div>
          <div class="tree-leg leg-right">
            <div style="font-size:12px;color:var(--neon-pink);font-weight:700;">RIGHT</div>
            <div class="leg-bar"><div class="leg-fill" id="rightFill" style="width:0%"></div></div>
            <div style="font-size:11px;color:var(--text-muted);" id="rightVol">0 TRX</div>
            <div style="font-size:11px;color:var(--text-muted);margin-top:6px;"><span id="rightDownlineCount">0</span> نفر</div>
            <div style="font-size:12px;color:var(--neon-pink);font-weight:700;margin-top:2px;" id="rightCommission">0 TRX</div>
          </div>
        </div>
        <div style="text-align:center;margin-top:14px;padding-top:14px;border-top:1px solid var(--glass-border);font-size:12px;color:var(--text-muted);">
          Total Downline: <span id="downlineCount" style="color:var(--text-primary);font-weight:700;">0</span>
        </div>
      </div>'''
content = content.replace(old_tree, new_tree, 1)

old_stats = '''        <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--glass-border);">
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
assert old_stats in content, "network-stats trailing block anchor not found"
new_stats = '''        <div style="display:flex;justify-content:space-between;padding:8px 0;">
          <span style="font-size:13px;color:var(--text-muted);">Bonus Cycles Earned</span>
          <span style="font-family:'Orbitron',sans-serif;font-size:14px;" id="cycleCount">0</span>
        </div>
      </div>
    </div>'''
content = content.replace(old_stats, new_stats, 1)

old_js = '''    document.getElementById('downlineCount').textContent = d.downline_count;
    document.getElementById('leftCommission').textContent = d.left_commission_trx.toFixed(2) + ' TRX';
    document.getElementById('rightCommission').textContent = d.right_commission_trx.toFixed(2) + ' TRX';'''
assert old_js in content, "loadReferralStats JS anchor not found"
new_js = '''    document.getElementById('downlineCount').textContent = d.downline_count;
    document.getElementById('leftDownlineCount').textContent = d.left_downline_count;
    document.getElementById('rightDownlineCount').textContent = d.right_downline_count;
    document.getElementById('leftCommission').textContent = d.left_commission_trx.toFixed(2) + ' TRX';
    document.getElementById('rightCommission').textContent = d.right_commission_trx.toFixed(2) + ' TRX';'''
content = content.replace(old_js, new_js, 1)

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("index.html: referral UI moved and left/right downline count added")
