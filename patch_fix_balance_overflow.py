with open("templates/index.html", "r", encoding="utf-8") as f:
    content = f.read()

old_css = '''.balance-chips-row { display: flex; gap: 5px; overflow-x: auto; scrollbar-width: none; flex: 1; justify-content: flex-end; }
.balance-chips-row::-webkit-scrollbar { display: none; }
.balance-chip {
  display: flex; align-items: center; gap: 4px; flex-shrink: 0;
  background: rgba(255,255,255,0.04); border: 1px solid var(--glass-border);
  backdrop-filter: blur(12px); padding: 5px 9px; border-radius: 999px;
  font-size: 11px; font-weight: 700; font-family: 'Orbitron', sans-serif;
}'''

new_css = '''.balance-chips-row { display: flex; gap: 4px; overflow-x: auto; scrollbar-width: none; flex: 1; justify-content: flex-start; min-width: 0; }
.balance-chips-row::-webkit-scrollbar { display: none; }
.balance-chip {
  display: flex; align-items: center; gap: 3px; flex-shrink: 0;
  background: rgba(255,255,255,0.04); border: 1px solid var(--glass-border);
  backdrop-filter: blur(12px); padding: 4px 7px; border-radius: 999px;
  font-size: 10px; font-weight: 700; font-family: 'Orbitron', sans-serif;
}'''

assert old_css in content, "balance chip CSS anchor not found"
content = content.replace(old_css, new_css, 1)

old_brand = '''.brand {
  font-family: 'Orbitron', sans-serif; font-weight: 900; font-size: 18px; letter-spacing: 2px;
  background: linear-gradient(90deg, var(--neon-cyan), var(--neon-purple));
  -webkit-background-clip: text; background-clip: text; color: transparent;
}'''
new_brand = '''.brand {
  font-family: 'Orbitron', sans-serif; font-weight: 900; font-size: 15px; letter-spacing: 1px;
  background: linear-gradient(90deg, var(--neon-cyan), var(--neon-purple));
  -webkit-background-clip: text; background-clip: text; color: transparent;
  flex-shrink: 0;
}'''
assert old_brand in content, "brand CSS anchor not found"
content = content.replace(old_brand, new_brand, 1)

old_icon = '''.chip-icon { width: 15px; height: 15px; border-radius: 50%; object-fit: cover; flex-shrink: 0; background: rgba(255,255,255,0.1); }'''
new_icon = '''.chip-icon { width: 13px; height: 13px; border-radius: 50%; object-fit: cover; flex-shrink: 0; background: rgba(255,255,255,0.1); }'''
assert old_icon in content, "chip-icon CSS anchor not found"
content = content.replace(old_icon, new_icon, 1)

with open("templates/index.html", "w", encoding="utf-8") as f:
    f.write(content)

print("index.html patched: balance bar overflow fixed")
