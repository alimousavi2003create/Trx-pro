with open("database.py", "r", encoding="utf-8") as f:
    content = f.read()

old_line = '        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS balance_usdt REAL DEFAULT 0")'
new_line = '''        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS balance_usdt REAL DEFAULT 0")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS tap_count_reset_at TIMESTAMP DEFAULT NOW()")'''
assert old_line in content, "balance_usdt ALTER TABLE anchor not found"
content = content.replace(old_line, new_line, 1)

with open("database.py", "w", encoding="utf-8") as f:
    f.write(content)

print("database.py tap reset column patch applied successfully")
