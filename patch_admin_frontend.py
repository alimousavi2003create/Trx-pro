with open("templates/index.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1) Add admin tab button to tabbar (only shows if user is admin, controlled by JS later)
old_tabbar_end = '''    <div class="tab-item" onclick="switchTab('profile')">
      <span class="tab-icon">👤</span>
      <span>Profile</span>
    </div>
  </div>'''
new_tabbar_end = '''    <div class="tab-item" onclick="switchTab('profile')">
      <span class="tab-icon">👤</span>
      <span>Profile</span>
    </div>
    <div class="tab-item hidden" id="adminTabBtn" onclick="switchTab('admin')">
      <span class="tab-icon">🛠️</span>
      <span>Admin</span>
    </div>
  </div>'''
assert old_tabbar_end in content, "tabbar anchor not found"
content = content.replace(old_tabbar_end, new_tabbar_end, 1)

# 2) Add admin tab content before closing </div> of .content, right after tab-profile block
old_profile_end = '''      <div class="tx-list" id="txList">
        <div style="font-size:13px;color:var(--text-muted);margin-bottom:12px;text-transform:uppercase;letter-spacing:1px;">Recent Transactions</div>
      </div>
    </div>
  </div>'''
new_profile_end = '''      <div class="tx-list" id="txList">
        <div style="font-size:13px;color:var(--text-muted);margin-bottom:12px;text-transform:uppercase;letter-spacing:1px;">Recent Transactions</div>
      </div>
    </div>

    <!-- TAB: Admin -->
    <div id="tab-admin" class="tab-content hidden">
      <div class="stats-grid" style="grid-template-columns: repeat(2, 1fr); margin-bottom:16px;">
        <div class="stat-card">
          <div class="stat-value" id="adminTotalUsers">0</div>
          <div class="stat-label">Total Users</div>
        </div>
        <div class="stat-card">
          <div class="stat-value" id="adminPendingCount">0</div>
          <div class="stat-label">Pending Withdrawals</div>
        </div>
      </div>

      <div class="wallet-card">
        <div class="wallet-header"><span class="wallet-title">Pool State</span></div>
        <div id="adminPoolList" style="font-size:12px;"></div>
      </div>

      <div class="wallet-card">
        <div class="wallet-header"><span class="wallet-title">Manual Credit</span></div>
        <input type="text" id="adminCreditUserId" placeholder="User ID" style="width:100%;box-sizing:border-box;padding:10px;border-radius:8px;background:rgba(255,255,255,0.06);border:1px solid #333;color:#fff;margin-bottom:8px;">
        <div style="display:flex;gap:8px;margin-bottom:8px;">
          <select id="adminCreditCurrency" style="flex:1;padding:10px;border-radius:8px;background:rgba(255,255,255,0.06);border:1px solid #333;color:#fff;">
            <option value="TRX">TRX</option>
            <option value="TON">TON</option>
            <option value="USDT">USDT</option>
          </select>
          <input type="text" id="adminCreditAmount" placeholder="Amount" inputmode="decimal" style="flex:1;padding:10px;border-radius:8px;background:rgba(255,255,255,0.06);border:1px solid #333;color:#fff;">
        </div>
        <button class="wallet-btn" style="width:100%;" onclick="adminSubmitCredit()">Credit User</button>
      </div>

      <div class="wallet-card">
        <div class="wallet-header"><span class="wallet-title">Pending Withdrawals</span></div>
        <div id="adminWithdrawalsList"></div>
      </div>

      <div class="wallet-card">
        <button class="wallet-btn" style="width:100%;color:var(--neon-pink);" onclick="adminResetPool()">Reset Pool (all currencies)</button>
      </div>
    </div>
  </div>'''
assert old_profile_end in content, "profile-end anchor not found"
content = content.replace(old_profile_end, new_profile_end, 1)

# 3) Add JS logic before closing </script>
old_init_call = "initAuth();\n</script>"
new_init_call = '''let isAdmin = false;

async function checkAdminStatus() {
  try {
    const r = await fetch(API_BASE + '/api/admin/check?user_id=' + encodeURIComponent(userId));
    const d = await r.json();
    if (d.success && d.is_admin) {
      isAdmin = true;
      document.getElementById('adminTabBtn').classList.remove('hidden');
    }
  } catch (e) { console.error('admin check failed', e); }
}

async function loadAdminDashboard() {
  if (!isAdmin) return;
  try {
    const r = await fetch(API_BASE + '/api/admin/dashboard?admin_id=' + encodeURIComponent(userId));
    const d = await r.json();
    if (!d.success) { showToast(d.error || 'Admin load failed', 'error'); return; }
    document.getElementById('adminTotalUsers').textContent = d.total_users;
    document.getElementById('adminPendingCount').textContent = d.pending_withdrawals.length;

    document.getElementById('adminPoolList').innerHTML = (d.pool || []).map(p => `
      <div style="display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid var(--glass-border);">
        <span>${p.currency}</span>
        <span>collected: ${(p.total_collected||0).toFixed(2)} / paid: ${(p.total_paid||0).toFixed(2)}</span>
      </div>`).join('') || '<div style="color:var(--text-muted);">No data</div>';

    document.getElementById('adminWithdrawalsList').innerHTML = (d.pending_withdrawals || []).map(w => `
      <div style="padding:10px 0;border-bottom:1px solid var(--glass-border);">
        <div style="font-size:12px;margin-bottom:6px;">#${w.id} · user ${w.user_id} · ${w.amount} ${w.currency}</div>
        <div style="font-size:11px;color:var(--text-muted);margin-bottom:8px;word-break:break-all;">to: ${w.destination_address}</div>
        <div style="display:flex;gap:8px;">
          <button class="wallet-btn" style="flex:1;" onclick="adminApproveWithdrawal(${w.id})">Approve</button>
          <button class="wallet-btn" style="flex:1;color:var(--neon-pink);" onclick="adminRejectWithdrawal(${w.id})">Reject</button>
        </div>
      </div>`).join('') || '<div style="color:var(--text-muted);">No pending withdrawals</div>';
  } catch (e) { showToast('Network error', 'error'); }
}

async function adminApproveWithdrawal(wid) {
  try {
    const r = await fetch(API_BASE + '/api/admin/withdraw/approve', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ admin_id: userId, withdrawal_id: wid })
    });
    const d = await r.json();
    showToast(d.message || d.error, d.success ? 'success' : 'error');
    if (d.success) loadAdminDashboard();
  } catch (e) { showToast('Network error', 'error'); }
}

async function adminRejectWithdrawal(wid) {
  try {
    const r = await fetch(API_BASE + '/api/admin/withdraw/reject', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ admin_id: userId, withdrawal_id: wid })
    });
    const d = await r.json();
    showToast(d.message || d.error, d.success ? 'success' : 'error');
    if (d.success) loadAdminDashboard();
  } catch (e) { showToast('Network error', 'error'); }
}

async function adminSubmitCredit() {
  const targetUserId = document.getElementById('adminCreditUserId').value.trim();
  const currency = document.getElementById('adminCreditCurrency').value;
  const amount = parseFloat(document.getElementById('adminCreditAmount').value);
  if (!targetUserId || !amount || amount <= 0) { showToast('Fill in user ID and a valid amount', 'error'); return; }
  try {
    const r = await fetch(API_BASE + '/api/admin/credit', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ admin_id: userId, target_user_id: targetUserId, currency, amount })
    });
    const d = await r.json();
    showToast(d.message || d.error, d.success ? 'success' : 'error');
    if (d.success) {
      document.getElementById('adminCreditUserId').value = '';
      document.getElementById('adminCreditAmount').value = '';
    }
  } catch (e) { showToast('Network error', 'error'); }
}

async function adminResetPool() {
  if (!confirm('Reset pool state for ALL currencies? This cannot be undone.')) return;
  try {
    const r = await fetch(API_BASE + '/api/admin/resetpool', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ admin_id: userId })
    });
    const d = await r.json();
    showToast(d.message || d.error, d.success ? 'success' : 'error');
    if (d.success) loadAdminDashboard();
  } catch (e) { showToast('Network error', 'error'); }
}

initAuth();
checkAdminStatus();
</script>'''
assert old_init_call in content, "init-call anchor not found"
content = content.replace(old_init_call, new_init_call, 1)

# 4) Hook admin dashboard load into switchTab
old_switch = '''  if (tab === 'crash') { startCrashPolling(); } else { stopCrashPolling(); }'''
new_switch = '''  if (tab === 'crash') { startCrashPolling(); } else { stopCrashPolling(); }
  if (tab === 'admin') { loadAdminDashboard(); }'''
assert old_switch in content, "switchTab anchor not found"
content = content.replace(old_switch, new_switch, 1)

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("index.html patched successfully")
