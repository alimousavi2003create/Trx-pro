with open("templates/index.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1) Add NFT tab button to tabbar, before the Admin button
old_tabbar = '''    <div class="tab-item hidden" id="adminTabBtn" onclick="switchTab('admin')">
      <span class="tab-icon">🛠️</span>
      <span>Admin</span>
    </div>
  </div>'''
new_tabbar = '''    <div class="tab-item" onclick="switchTab('nft')">
      <span class="tab-icon">🖼️</span>
      <span>NFT</span>
    </div>
    <div class="tab-item hidden" id="adminTabBtn" onclick="switchTab('admin')">
      <span class="tab-icon">🛠️</span>
      <span>Admin</span>
    </div>
  </div>'''
assert old_tabbar in content, "tabbar anchor not found"
content = content.replace(old_tabbar, new_tabbar, 1)

# 2) Add NFT tab content before the Admin tab content
old_admin_comment = "    <!-- TAB: Admin -->"
new_nft_tab = '''    <!-- TAB: NFT -->
    <div id="tab-nft" class="tab-content hidden">
      <div style="display:flex;gap:8px;margin-bottom:16px;">
        <button class="ref-btn" style="flex:1;" onclick="switchNftView('mint')" id="nftViewBtnMint">Create</button>
        <button class="ref-btn" style="flex:1;" onclick="switchNftView('mine')" id="nftViewBtnMine">My NFTs</button>
        <button class="ref-btn" style="flex:1;" onclick="switchNftView('market')" id="nftViewBtnMarket">Market</button>
      </div>

      <div id="nftViewMint">
        <div class="wallet-card">
          <div class="wallet-header"><span class="wallet-title">Create NFT</span></div>
          <div style="font-size:12px;color:var(--text-muted);margin-bottom:12px;">
            Mint fee: 10 USDT / 111 TRX / 2.05 TON (choose currency below)
          </div>
          <input type="file" id="nftImageInput" accept="image/*" style="display:none;" onchange="handleNftImageSelect(event)">
          <div id="nftImagePreviewBox" onclick="document.getElementById('nftImageInput').click()"
               style="width:100%;aspect-ratio:1;border-radius:12px;border:2px dashed #444;display:flex;align-items:center;justify-content:center;cursor:pointer;margin-bottom:12px;background:rgba(255,255,255,0.03);overflow:hidden;">
            <span style="color:var(--text-muted);font-size:13px;">Tap to choose image</span>
          </div>
          <input type="text" id="nftNameInput" placeholder="NFT name" maxlength="40"
                 style="width:100%;box-sizing:border-box;padding:10px;border-radius:8px;background:rgba(255,255,255,0.06);border:1px solid #333;color:#fff;margin-bottom:8px;">
          <select id="nftMintCurrency" style="width:100%;padding:10px;border-radius:8px;background:rgba(255,255,255,0.06);border:1px solid #333;color:#fff;margin-bottom:12px;">
            <option value="USDT">Pay with USDT (10)</option>
            <option value="TRX">Pay with TRX (111)</option>
            <option value="TON">Pay with TON (2.05)</option>
          </select>
          <button class="wallet-btn" style="width:100%;" onclick="mintNft()">Mint NFT</button>
        </div>
      </div>

      <div id="nftViewMine" class="hidden">
        <div id="myNftsList"></div>
      </div>

      <div id="nftViewMarket" class="hidden">
        <div id="marketNftsList"></div>
      </div>
    </div>

    <!-- TAB: Admin -->'''
assert old_admin_comment in content, "admin comment anchor not found"
content = content.replace(old_admin_comment, new_nft_tab, 1)

# 3) Hook nft tab load into switchTab
old_switch = '''  if (tab === 'admin') { loadAdminDashboard(); }'''
new_switch = '''  if (tab === 'admin') { loadAdminDashboard(); }
  if (tab === 'nft') { switchNftView('mint'); }'''
assert old_switch in content, "switchTab admin-hook anchor not found"
content = content.replace(old_switch, new_switch, 1)

# 4) Add all NFT JS logic before checkAdminStatus(); (end of script)
old_tail = '''initAuth();
checkAdminStatus();
</script>'''
new_tail = '''let nftSelectedImageData = null;

function switchNftView(view) {
  document.getElementById('nftViewMint').classList.add('hidden');
  document.getElementById('nftViewMine').classList.add('hidden');
  document.getElementById('nftViewMarket').classList.add('hidden');
  document.getElementById('nftViewBtnMint').style.opacity = '0.5';
  document.getElementById('nftViewBtnMine').style.opacity = '0.5';
  document.getElementById('nftViewBtnMarket').style.opacity = '0.5';
  if (view === 'mint') {
    document.getElementById('nftViewMint').classList.remove('hidden');
    document.getElementById('nftViewBtnMint').style.opacity = '1';
  } else if (view === 'mine') {
    document.getElementById('nftViewMine').classList.remove('hidden');
    document.getElementById('nftViewBtnMine').style.opacity = '1';
    loadMyNfts();
  } else if (view === 'market') {
    document.getElementById('nftViewMarket').classList.remove('hidden');
    document.getElementById('nftViewBtnMarket').style.opacity = '1';
    loadMarket();
  }
}

function handleNftImageSelect(event) {
  const file = event.target.files[0];
  if (!file) return;
  if (file.size > 2 * 1024 * 1024) {
    showToast('Image too large (max 2MB)', 'error');
    return;
  }
  const reader = new FileReader();
  reader.onload = (e) => {
    nftSelectedImageData = e.target.result;
    document.getElementById('nftImagePreviewBox').innerHTML =
      `<img src="${nftSelectedImageData}" style="width:100%;height:100%;object-fit:cover;">`;
  };
  reader.readAsDataURL(file);
}

async function mintNft() {
  const name = document.getElementById('nftNameInput').value.trim();
  const currency = document.getElementById('nftMintCurrency').value;
  if (!name) { showToast('Enter a name for your NFT', 'error'); return; }
  if (!nftSelectedImageData) { showToast('Choose an image first', 'error'); return; }
  try {
    const r = await fetch(API_BASE + '/api/nft/mint', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, name, currency, image_data: nftSelectedImageData })
    });
    const d = await r.json();
    if (d.success) {
      showToast(`NFT minted! Fee: ${d.fee_charged} ${d.currency}`, 'success');
      document.getElementById('nftNameInput').value = '';
      nftSelectedImageData = null;
      document.getElementById('nftImagePreviewBox').innerHTML = '<span style="color:var(--text-muted);font-size:13px;">Tap to choose image</span>';
      fetchUserData();
      switchNftView('mine');
    } else {
      showToast(d.error || 'Mint failed', 'error');
    }
  } catch (e) { showToast('Network error', 'error'); }
}

async function loadNftImageInto(nftId, imgElId) {
  try {
    const r = await fetch(API_BASE + '/api/nft/image/' + nftId);
    const d = await r.json();
    const el = document.getElementById(imgElId);
    if (d.success && el) el.src = d.image_data;
  } catch (e) {}
}

async function loadMyNfts() {
  try {
    const r = await fetch(API_BASE + '/api/nft/mine?user_id=' + encodeURIComponent(userId));
    const d = await r.json();
    const container = document.getElementById('myNftsList');
    if (!d.success || !d.nfts.length) {
      container.innerHTML = '<div style="color:var(--text-muted);text-align:center;padding:20px;">No NFTs yet. Create one!</div>';
      return;
    }
    container.innerHTML = d.nfts.map(n => `
      <div class="wallet-card">
        <div style="display:flex;gap:12px;">
          <img id="mynft-img-${n.id}" style="width:70px;height:70px;border-radius:10px;object-fit:cover;background:rgba(255,255,255,0.05);">
          <div style="flex:1;">
            <div style="font-weight:600;margin-bottom:4px;">${n.name}</div>
            <div style="font-size:11px;color:var(--text-muted);margin-bottom:8px;">
              ${n.is_listed ? `Listed: ${n.price} ${n.currency}` : 'Not listed'}
            </div>
            <div style="display:flex;gap:6px;">
              <button class="ref-btn" style="flex:1;font-size:11px;padding:6px;" onclick="promptListNft(${n.id})">${n.is_listed ? 'Edit Price' : 'List for Sale'}</button>
              ${n.is_listed ? `<button class="ref-btn" style="flex:1;font-size:11px;padding:6px;" onclick="unlistNft(${n.id})">Unlist</button>` : ''}
            </div>
          </div>
        </div>
      </div>`).join('');
    d.nfts.forEach(n => loadNftImageInto(n.id, `mynft-img-${n.id}`));
  } catch (e) { showToast('Network error', 'error'); }
}

function promptListNft(nftId) {
  const price = prompt('Set price (number):');
  if (!price || isNaN(parseFloat(price)) || parseFloat(price) <= 0) { if (price !== null) showToast('Invalid price', 'error'); return; }
  const currency = prompt('Currency (TRX / TON / USDT):', 'USDT');
  if (!currency || !['TRX', 'TON', 'USDT'].includes(currency.toUpperCase())) { showToast('Invalid currency', 'error'); return; }
  listNft(nftId, parseFloat(price), currency.toUpperCase());
}

async function listNft(nftId, price, currency) {
  try {
    const r = await fetch(API_BASE + '/api/nft/list', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, nft_id: nftId, price, currency, is_listed: true })
    });
    const d = await r.json();
    showToast(d.message || d.error, d.success ? 'success' : 'error');
    if (d.success) loadMyNfts();
  } catch (e) { showToast('Network error', 'error'); }
}

async function unlistNft(nftId) {
  try {
    const r = await fetch(API_BASE + '/api/nft/unlist', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, nft_id: nftId })
    });
    const d = await r.json();
    showToast(d.success ? 'Unlisted' : (d.error || 'Failed'), d.success ? 'success' : 'error');
    if (d.success) loadMyNfts();
  } catch (e) { showToast('Network error', 'error'); }
}

async function loadMarket() {
  try {
    const r = await fetch(API_BASE + '/api/nft/market');
    const d = await r.json();
    const container = document.getElementById('marketNftsList');
    if (!d.success || !d.listings.length) {
      container.innerHTML = '<div style="color:var(--text-muted);text-align:center;padding:20px;">No listings right now.</div>';
      return;
    }
    container.innerHTML = d.listings.map(n => `
      <div class="wallet-card">
        <div style="display:flex;gap:12px;">
          <img id="market-img-${n.id}" style="width:70px;height:70px;border-radius:10px;object-fit:cover;background:rgba(255,255,255,0.05);">
          <div style="flex:1;">
            <div style="font-weight:600;margin-bottom:4px;">${n.name}</div>
            <div style="font-size:12px;color:var(--neon-yellow);margin-bottom:8px;">${n.price} ${n.currency}</div>
            <button class="wallet-btn" style="width:100%;font-size:12px;padding:8px;" onclick="buyNft(${n.id})">Buy Now</button>
          </div>
        </div>
      </div>`).join('');
    d.listings.forEach(n => loadNftImageInto(n.id, `market-img-${n.id}`));
  } catch (e) { showToast('Network error', 'error'); }
}

async function buyNft(nftId) {
  if (!confirm('Buy this NFT? A 5% buyer fee applies.')) return;
  try {
    const r = await fetch(API_BASE + '/api/nft/buy', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, nft_id: nftId })
    });
    const d = await r.json();
    if (d.success) {
      showToast(`Bought! Paid ${d.buyer_paid} ${d.currency}`, 'success');
      fetchUserData();
      loadMarket();
    } else {
      showToast(d.error || 'Purchase failed', 'error');
    }
  } catch (e) { showToast('Network error', 'error'); }
}

initAuth();
checkAdminStatus();
</script>'''
assert old_tail in content, "tail anchor (initAuth/checkAdminStatus) not found"
content = content.replace(old_tail, new_tail, 1)

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("index.html patched with full NFT tab UI successfully")
