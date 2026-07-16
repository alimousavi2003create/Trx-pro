with open("templates/index.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1) CSS: add compact styles for the redesigned topbar
old_balance_chip_css = '''.balance-chip {
  display: flex; align-items: center; gap: 6px;
  background: rgba(255,255,255,0.04); border: 1px solid var(--glass-border);
  backdrop-filter: blur(12px); padding: 6px 12px; border-radius: 999px;
  font-size: 13px; font-weight: 700; font-family: 'Orbitron', sans-serif;
}
.balance-chip .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--neon-cyan); box-shadow: 0 0 8px var(--neon-cyan); animation: pulse-dot 2s infinite; }'''
new_balance_chip_css = '''.topbar { flex-wrap: nowrap; gap: 6px; }
.balance-chips-row { display: flex; gap: 5px; overflow-x: auto; scrollbar-width: none; flex: 1; justify-content: flex-end; }
.balance-chips-row::-webkit-scrollbar { display: none; }
.balance-chip {
  display: flex; align-items: center; gap: 4px; flex-shrink: 0;
  background: rgba(255,255,255,0.04); border: 1px solid var(--glass-border);
  backdrop-filter: blur(12px); padding: 5px 9px; border-radius: 999px;
  font-size: 11px; font-weight: 700; font-family: 'Orbitron', sans-serif;
}
.balance-chip .dot { width: 6px; height: 6px; border-radius: 50%; background: var(--neon-cyan); box-shadow: 0 0 8px var(--neon-cyan); animation: pulse-dot 2s infinite; }
.chip-icon { width: 15px; height: 15px; border-radius: 50%; object-fit: cover; flex-shrink: 0; background: rgba(255,255,255,0.1); }'''
assert old_balance_chip_css in content, "balance-chip CSS anchor not found"
content = content.replace(old_balance_chip_css, new_balance_chip_css, 1)

# 2) HTML: replace the three chips block with icons, no currency text labels, wrapped in scrollable row
old_topbar_html = '''  <div class="topbar">
    <div class="brand">TRX PRO</div>
    <div class="balance-chip">
      <span class="dot"></span>
      🔺 <span id="topBalance">0</span> TRX
    </div>
    <div class="balance-chip" style="margin-left:6px;">
      <span class="dot"></span>
      💎 <span id="topBalanceTON">0</span> TON
    </div>
    <div class="balance-chip" style="margin-left:6px;">
      <span class="dot"></span>
      💵 <span id="topBalanceUSDT">0</span> USDT
    </div>
  </div>'''
new_topbar_html = '''  <div class="topbar">
    <div class="brand">TRX PRO</div>
    <div class="balance-chips-row">
      <div class="balance-chip">
        <img src="/static/icons/trx.jpg" class="chip-icon" alt="TRX">
        <span id="topBalance">0</span>
      </div>
      <div class="balance-chip">
        <img src="/static/icons/ton.jpg" class="chip-icon" alt="TON">
        <span id="topBalanceTON">0</span>
      </div>
      <div class="balance-chip">
        <img src="/static/icons/usdt.jpg" class="chip-icon" alt="USDT">
        <span id="topBalanceUSDT">0</span>
      </div>
    </div>
  </div>'''
assert old_topbar_html in content, "topbar HTML anchor not found"
content = content.replace(old_topbar_html, new_topbar_html, 1)

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("topbar fix applied successfully")
