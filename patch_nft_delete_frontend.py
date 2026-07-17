with open("templates/index.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1) Add Delete button to each card in loadMyNfts()
old_card = '''            <div style="display:flex;gap:6px;">
              <button class="ref-btn" style="flex:1;font-size:11px;padding:6px;" onclick="promptListNft(${n.id})">${n.is_listed ? 'Edit Price' : 'List for Sale'}</button>
              ${n.is_listed ? `<button class="ref-btn" style="flex:1;font-size:11px;padding:6px;" onclick="unlistNft(${n.id})">Unlist</button>` : ''}
            </div>'''
new_card = '''            <div style="display:flex;gap:6px;">
              <button class="ref-btn" style="flex:1;font-size:11px;padding:6px;" onclick="promptListNft(${n.id})">${n.is_listed ? 'Edit Price' : 'List for Sale'}</button>
              ${n.is_listed ? `<button class="ref-btn" style="flex:1;font-size:11px;padding:6px;" onclick="unlistNft(${n.id})">Unlist</button>` : ''}
            </div>
            <button class="ref-btn" style="width:100%;font-size:11px;padding:6px;margin-top:6px;color:var(--neon-pink);" onclick="deleteNft(${n.id})">Delete NFT</button>'''
assert old_card in content, "my-nft card anchor not found"
content = content.replace(old_card, new_card, 1)

# 2) Add deleteNft() function right before loadMarket()
old_market_fn_start = "async function loadMarket() {"
new_market_fn_start = '''async function deleteNft(nftId) {
  if (!confirm('Delete this NFT permanently? If a mint fee was paid, it will be refunded to your balance.')) return;
  try {
    const r = await fetch(API_BASE + '/api/nft/delete', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, nft_id: nftId })
    });
    const d = await r.json();
    if (d.success) {
      let msg = 'NFT deleted';
      if (d.refunded_amount) msg += ` — refunded ${d.refunded_amount} ${d.refunded_currency}`;
      showToast(msg, 'success');
      if (typeof fetchUserData === 'function') fetchUserData();
      loadMyNfts();
    } else {
      showToast(d.error || 'Delete failed', 'error');
    }
  } catch (e) { showToast('Network error', 'error'); }
}

async function loadMarket() {'''
assert old_market_fn_start in content, "loadMarket anchor not found"
content = content.replace(old_market_fn_start, new_market_fn_start, 1)

# 3) Guard fetchUserData() calls to avoid false "Network error" toast if function name differs
occurrences_old = "      fetchUserData();\n      switchNftView('mine');"
occurrences_new = "      if (typeof fetchUserData === 'function') fetchUserData();\n      switchNftView('mine');"
if occurrences_old in content:
    content = content.replace(occurrences_old, occurrences_new, 1)

buy_old = "      fetchUserData();\n      loadMarket();"
buy_new = "      if (typeof fetchUserData === 'function') fetchUserData();\n      loadMarket();"
if buy_old in content:
    content = content.replace(buy_old, buy_new, 1)

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("index.html patched with delete button and safe balance refresh")
