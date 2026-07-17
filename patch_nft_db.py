with open("database.py", "r", encoding="utf-8") as f:
    content = f.read()

anchor = "def init_db():"
assert anchor in content, "init_db anchor not found in database.py"

new_table_sql = '''
        c.execute("""
            CREATE TABLE IF NOT EXISTS nfts (
                id SERIAL PRIMARY KEY,
                owner_id TEXT NOT NULL,
                creator_id TEXT NOT NULL,
                name TEXT NOT NULL,
                image_data TEXT NOT NULL,
                price NUMERIC,
                currency TEXT,
                is_listed BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
'''

idx = content.index(anchor)
insert_point = content.index('c.execute("""', idx)
content = content[:insert_point] + new_table_sql.strip() + "\n\n        " + content[insert_point:]

with open("database.py", "w", encoding="utf-8") as f:
    f.write(content)

print("database.py patched with nfts table")
