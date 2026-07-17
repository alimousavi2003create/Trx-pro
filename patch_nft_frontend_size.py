with open("templates/index.html", "r", encoding="utf-8") as f:
    content = f.read()

old_check = '''  if (file.size > 2 * 1024 * 1024) {
    showToast('Image too large (max 2MB)', 'error');
    return;
  }'''
new_check = '''  if (file.size > 5 * 1024 * 1024) {
    showToast('Image too large (max 5MB)', 'error');
    return;
  }'''
assert old_check in content, "frontend image size check anchor not found"
content = content.replace(old_check, new_check, 1)

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("index.html updated: frontend NFT image limit raised to 5MB")
