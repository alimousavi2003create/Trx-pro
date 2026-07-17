with open("database.py", "r", encoding="utf-8") as f:
    content = f.read()

old_line = '        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS tap_count_reset_at TIMESTAMP DEFAULT NOW()")'
new_line = '''        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS tap_count_reset_at TIMESTAMP DEFAULT NOW()")
        c.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_mentioned_at TIMESTAMP")'''
assert old_line in content, "tap_count_reset_at anchor not found"
content = content.replace(old_line, new_line, 1)

with open("database.py", "w", encoding="utf-8") as f:
    f.write(content)

print("database.py: last_mentioned_at column added")
