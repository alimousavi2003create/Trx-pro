with open("templates/index.html", "r", encoding="utf-8") as f:
    content = f.read()

# 1) Change file input hiding method from display:none to a safer hidden style
old_input = '''<input type="file" id="nftImageInput" accept="image/*" style="display:none;" onchange="handleNftImageSelect(event)">'''
new_input = '''<input type="file" id="nftImageInput" accept="image/*" style="position:absolute;width:1px;height:1px;opacity:0;overflow:hidden;" onchange="handleNftImageSelect(event)">'''
assert old_input in content, "file input anchor not found"
content = content.replace(old_input, new_input, 1)

# 2) Make mintNft() read the file directly as a fallback if nftSelectedImageData wasn't set by onchange
old_mint_fn = '''async function mintNft() {
  const name = document.getElementById('nftNameInput').value.trim();
  const currency = document.getElementById('nftMintCurrency').value;
  if (!name) { showToast('Enter a name for your NFT', 'error'); return; }
  if (!nftSelectedImageData) { showToast('Choose an image first', 'error'); return; }
  try {'''

new_mint_fn = '''async function mintNftWithImage(imageData) {
  const name = document.getElementById('nftNameInput').value.trim();
  const currency = document.getElementById('nftMintCurrency').value;
  try {
    const r = await fetch(API_BASE + '/api/nft/mint', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, name, currency, image_data: imageData })
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

async function mintNft() {
  const name = document.getElementById('nftNameInput').value.trim();
  if (!name) { showToast('Enter a name for your NFT', 'error'); return; }

  if (nftSelectedImageData) {
    mintNftWithImage(nftSelectedImageData);
    return;
  }

  const fileInput = document.getElementById('nftImageInput');
  const file = fileInput.files && fileInput.files[0];
  if (!file) { showToast('Choose an image first', 'error'); return; }

  const reader = new FileReader();
  reader.onload = (e) => {
    nftSelectedImageData = e.target.result;
    mintNftWithImage(nftSelectedImageData);
  };
  reader.onerror = () => { showToast('Failed to read image, try another one', 'error'); };
  reader.readAsDataURL(file);
  return;

  const currency = document.getElementById('nftMintCurrency').value;
  try {'''

assert old_mint_fn in content, "mintNft function anchor not found"
content = content.replace(old_mint_fn, new_mint_fn, 1)

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("index.html patched with file input fallback fix")
