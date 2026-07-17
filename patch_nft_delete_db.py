with open("database.py", "r", encoding="utf-8") as f:
    content = f.read()

anchor = '''                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)'''

assert anchor in content, "nfts table closing anchor not found"

alter_sql = '''                created_at TIMESTAMP DEFAULT NOW(),
                updated_at TIMESTAMP DEFAULT NOW()
            )
        """)
        c.execute("""
            ALTER TABLE nfts ADD COLUMN IF NOT EXISTS mint_fee_amount NUMERIC
        """)
        c.execute("""
            ALTER TABLE nfts ADD COLUMN IF NOT EXISTS mint_fee_currency TEXT
        """)'''

content = content.replace(anchor, alter_sql, 1)

with open("database.py", "w", encoding="utf-8") as f:
    f.write(content)

print("database.py patched with nft mint fee tracking columns")
