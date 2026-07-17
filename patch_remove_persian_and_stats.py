with open("templates/index.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1) Remove Persian "نفر" word, replace with "Users"
old_left_count = '<div style="font-size:11px;color:var(--text-muted);margin-top:6px;"><span id="leftDownlineCount">0</span> نفر</div>'
new_left_count = '<div style="font-size:11px;color:var(--text-muted);margin-top:6px;"><span id="leftDownlineCount">0</span> Users</div>'
assert old_left_count in content, "left downline count anchor not found"
content = content.replace(old_left_count, new_left_count, 1)

old_right_count = '<div style="font-size:11px;color:var(--text-muted);margin-top:6px;"><span id="rightDownlineCount">0</span> نفر</div>'
new_right_count = '<div style="font-size:11px;color:var(--text-muted);margin-top:6px;"><span id="rightDownlineCount">0</span> Users</div>'
assert old_right_count in content, "right downline count anchor not found"
content = content.replace(old_right_count, new_right_count, 1)

# 2) Remove the entire "Network Stats" wallet-card block completely
old_network_stats_block = '''      <div class="wallet-card">
        <div class="wallet-header">
          <span class="wallet-title">Network Stats</span>
        </div>
        <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--glass-border);">
          <span style="font-size:13px;color:var(--text-muted);">Left Volume</span>
          <span style="font-family:'Orbitron',sans-serif;font-size:14px;color:var(--neon-cyan);" id="netLeft">0 TRX</span>
        </div>
        <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--glass-border);">
          <span style="font-size:13px;color:var(--text-muted);">Right Volume</span>
          <span style="font-family:'Orbitron',sans-serif;font-size:14px;color:var(--neon-pink);" id="netRight">0 TRX</span>
        </div>
        <div style="display:flex;justify-content:space-between;padding:8px 0;border-bottom:1px solid var(--glass-border);">
          <span style="font-size:13px;color:var(--text-muted);">Next Bonus</span>
          <span style="font-family:'Orbitron',sans-serif;font-size:14px;color:var(--neon-yellow);" id="nextBonusAmount">400 TRX</span>
        </div>
        <div style="display:flex;justify-content:space-between;padding:8px 0;">
          <span style="font-size:13px;color:var(--text-muted);">Bonus Cycles Earned</span>
          <span style="font-family:'Orbitron',sans-serif;font-size:14px;" id="cycleCount">0</span>
        </div>
      </div>
    </div>'''
new_network_stats_block = '''    </div>'''
assert old_network_stats_block in content, "Network Stats block anchor not found"
content = content.replace(old_network_stats_block, new_network_stats_block, 1)

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("index.html: Persian word removed, Network Stats card fully deleted")
