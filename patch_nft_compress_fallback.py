with open("templates/index.html", "r", encoding="utf-8") as f:
    content = f.read()

old_select = '''  document.getElementById('nftImagePreviewBox').innerHTML = '<span style="color:var(--text-muted);font-size:13px;">Processing image...</span>';
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

new_select = '''  document.getElementById('nftImagePreviewBox').innerHTML = '<span style="color:var(--text-muted);font-size:13px;">Processing image...</span>';
  try {
    let compressed = await compressImageFile(file, 800, 0.75);
    let sizeBytes = Math.ceil((compressed.length * 3) / 4);
    if (sizeBytes > 1.5 * 1024 * 1024) {
      compressed = await compressImageFile(file, 600, 0.6);
    }
    nftSelectedImageData = compressed;
  } catch (e) {
    console.error('Compression failed, using raw image', e);
    try {
      nftSelectedImageData = await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (ev) => resolve(ev.target.result);
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });
    } catch (e2) {
      showToast('Failed to load image, try another one', 'error');
      document.getElementById('nftImagePreviewBox').innerHTML = '<span style="color:var(--text-muted);font-size:13px;">Tap to choose image</span>';
      return;
    }
  }
  document.getElementById('nftImagePreviewBox').innerHTML =
    `<img src="${nftSelectedImageData}" style="width:100%;height:100%;object-fit:cover;">`;
}'''

assert old_select in content, "handleNftImageSelect body anchor not found"
content = content.replace(old_select, new_select, 1)

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("index.html patched with compression fallback")
