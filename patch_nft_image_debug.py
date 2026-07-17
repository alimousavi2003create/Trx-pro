with open("templates/index.html", "r", encoding="utf-8") as f:
    content = f.read()

old_catch = '''    } catch (e2) {
      showToast('Failed to load image, try another one', 'error');
      document.getElementById('nftImagePreviewBox').innerHTML = '<span style="color:var(--text-muted);font-size:13px;">Tap to choose image</span>';
      return;
    }'''
assert old_catch in content, "e2 catch anchor not found"
new_catch = '''    } catch (e2) {
      console.error('NFT image load failed completely', e2);
      const fileTypeInfo = file && file.type ? file.type : 'unknown type';
      showToast(`Failed to load image (${fileTypeInfo}). Try a screenshot or a JPG/PNG file instead of a camera photo.`, 'error');
      document.getElementById('nftImagePreviewBox').innerHTML = '<span style="color:var(--text-muted);font-size:13px;">Tap to choose image</span>';
      return;
    }'''
content = content.replace(old_catch, new_catch, 1)

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("index.html: NFT image error message now shows file type for diagnosis")
