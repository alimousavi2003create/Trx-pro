with open("templates/index.html", "r", encoding="utf-8") as f:
    content = f.read()

old_handler = '''function handleNftImageSelect(event) {
  const file = event.target.files[0];
  if (!file) return;
  if (file.size > 5 * 1024 * 1024) {
    showToast('Image too large (max 5MB)', 'error');
    return;
  }
  const reader = new FileReader();
  reader.onload = (e) => {
    nftSelectedImageData = e.target.result;
    document.getElementById('nftImagePreviewBox').innerHTML =
      `<img src="${nftSelectedImageData}" style="width:100%;height:100%;object-fit:cover;">`;
  };
  reader.readAsDataURL(file);
}'''

new_handler = '''function compressImageFile(file, maxDim, quality) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const reader = new FileReader();
    reader.onload = (e) => {
      img.onload = () => {
        let w = img.width, h = img.height;
        if (w > maxDim || h > maxDim) {
          if (w > h) { h = Math.round(h * (maxDim / w)); w = maxDim; }
          else { w = Math.round(w * (maxDim / h)); h = maxDim; }
        }
        const canvas = document.createElement('canvas');
        canvas.width = w; canvas.height = h;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, w, h);
        resolve(canvas.toDataURL('image/jpeg', quality));
      };
      img.onerror = reject;
      img.src = e.target.result;
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

async function handleNftImageSelect(event) {
  const file = event.target.files[0];
  if (!file) return;
  if (file.size > 15 * 1024 * 1024) {
    showToast('Image too large (max 15MB before compression)', 'error');
    return;
  }
  document.getElementById('nftImagePreviewBox').innerHTML = '<span style="color:var(--text-muted);font-size:13px;">Processing image...</span>';
  try {
    let compressed = await compressImageFile(file, 800, 0.75);
    let sizeBytes = Math.ceil((compressed.length * 3) / 4);
    if (sizeBytes > 1.5 * 1024 * 1024) {
      compressed = await compressImageFile(file, 600, 0.6);
    }
    nftSelectedImageData = compressed;
    document.getElementById('nftImagePreviewBox').innerHTML =
      `<img src="${nftSelectedImageData}" style="width:100%;height:100%;object-fit:cover;">`;
  } catch (e) {
    showToast('Failed to process image, try another one', 'error');
    document.getElementById('nftImagePreviewBox').innerHTML = '<span style="color:var(--text-muted);font-size:13px;">Tap to choose image</span>';
  }
}'''

assert old_handler in content, "handleNftImageSelect anchor not found"
content = content.replace(old_handler, new_handler, 1)

# Also update the fallback direct-read path inside mintNft() to compress too
old_fallback = '''  const fileInput = document.getElementById('nftImageInput');
  const file = fileInput.files && fileInput.files[0];
  if (!file) { showToast('Choose an image first', 'error'); return; }

  const reader = new FileReader();
  reader.onload = (e) => {
    nftSelectedImageData = e.target.result;
    mintNftWithImage(nftSelectedImageData);
  };
  reader.onerror = () => { showToast('Failed to read image, try another one', 'error'); };
  reader.readAsDataURL(file);
  return;'''

new_fallback = '''  const fileInput = document.getElementById('nftImageInput');
  const file = fileInput.files && fileInput.files[0];
  if (!file) { showToast('Choose an image first', 'error'); return; }

  try {
    const compressed = await compressImageFile(file, 800, 0.75);
    nftSelectedImageData = compressed;
    mintNftWithImage(nftSelectedImageData);
  } catch (e) {
    showToast('Failed to process image, try another one', 'error');
  }
  return;'''

assert old_fallback in content, "mintNft fallback anchor not found"
content = content.replace(old_fallback, new_fallback, 1)

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("index.html patched with client-side image compression")
