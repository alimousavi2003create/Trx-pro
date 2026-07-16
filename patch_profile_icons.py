with open("templates/index.html", "r", encoding="utf-8") as f:
    content = f.read()

old_wallets = '''      <div class="wallet-card">
        <div class="wallet-header">
          <span class="wallet-title">🔺 TRX Balance</span>
        </div>
        <div class="wallet-amount" id="walletTRX">0 TRX</div>
        <div class="wallet-actions">
          <button class="wallet-btn" onclick="openDepositModal('TRX')">Deposit</button>
          <button class="wallet-btn" onclick="openWithdrawModal('TRX')">Withdraw</button>
        </div>
      </div>
      <div class="wallet-card">
        <div class="wallet-header">
          <span class="wallet-title">💎 TON Balance</span>
        </div>
        <div class="wallet-amount" id="walletTON">0 TON</div>
        <div class="wallet-actions">
          <button class="wallet-btn" onclick="openDepositModal('TON')">Deposit</button>
          <button class="wallet-btn" onclick="openWithdrawModal('TON')">Withdraw</button>
        </div>
      </div>
      <div class="wallet-card">
        <div class="wallet-header">
          <span class="wallet-title">💵 USDT Balance</span>
        </div>
        <div class="wallet-amount" id="walletUSDT">0 USDT</div>
        <div class="wallet-actions">
          <button class="wallet-btn" onclick="openDepositModal('USDT')">Deposit</button>
          <button class="wallet-btn" onclick="openWithdrawModal('USDT')">Withdraw</button>
        </div>
      </div>'''
new_wallets = '''      <div class="wallet-card">
        <div class="wallet-header">
          <span class="wallet-title" style="display:flex;align-items:center;gap:6px;"><img src="/static/icons/trx.jpg" style="width:18px;height:18px;border-radius:50%;object-fit:cover;"> TRX Balance</span>
        </div>
        <div class="wallet-amount" id="walletTRX">0 TRX</div>
        <div class="wallet-actions">
          <button class="wallet-btn" onclick="openDepositModal('TRX')">Deposit</button>
          <button class="wallet-btn" onclick="openWithdrawModal('TRX')">Withdraw</button>
        </div>
      </div>
      <div class="wallet-card">
        <div class="wallet-header">
          <span class="wallet-title" style="display:flex;align-items:center;gap:6px;"><img src="/static/icons/ton.jpg" style="width:18px;height:18px;border-radius:50%;object-fit:cover;"> TON Balance</span>
        </div>
        <div class="wallet-amount" id="walletTON">0 TON</div>
        <div class="wallet-actions">
          <button class="wallet-btn" onclick="openDepositModal('TON')">Deposit</button>
          <button class="wallet-btn" onclick="openWithdrawModal('TON')">Withdraw</button>
        </div>
      </div>
      <div class="wallet-card">
        <div class="wallet-header">
          <span class="wallet-title" style="display:flex;align-items:center;gap:6px;"><img src="/static/icons/usdt.jpg" style="width:18px;height:18px;border-radius:50%;object-fit:cover;"> USDT Balance</span>
        </div>
        <div class="wallet-amount" id="walletUSDT">0 USDT</div>
        <div class="wallet-actions">
          <button class="wallet-btn" onclick="openDepositModal('USDT')">Deposit</button>
          <button class="wallet-btn" onclick="openWithdrawModal('USDT')">Withdraw</button>
        </div>
      </div>'''
assert old_wallets in content, "wallet-card block anchor not found"
content = content.replace(old_wallets, new_wallets, 1)

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("profile icons patch applied successfully")
