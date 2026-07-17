with open("templates/index.html", "r", encoding="utf-8") as f:
    content = f.read()

old_line = "  document.getElementById('netLeft').textContent = leftVol.toFixed(2) + ' TRX';\n  document.getElementById('netRight').textContent = rightVol.toFixed(2) + ' TRX';"
new_line = "  const netLeftEl = document.getElementById('netLeft'); if (netLeftEl) netLeftEl.textContent = leftVol.toFixed(2) + ' TRX';\n  const netRightEl = document.getElementById('netRight'); if (netRightEl) netRightEl.textContent = rightVol.toFixed(2) + ' TRX';"
assert old_line in content, "netLeft/netRight update lines anchor not found"
content = content.replace(old_line, new_line, 1)

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("index.html: safe null-check added for removed netLeft/netRight elements")
