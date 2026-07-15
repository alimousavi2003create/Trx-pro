with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

old_items = '''    default_items = [
        ("auto_miner_v1", "Auto Miner v1", "Auto-mine 0.5 TRX per hour",
         "auto_mine", 0.5, 500, None, 30, "Rare"),
        ("energy_core_v1", "Energy Core", "+50 Max Energy",
         "energy", 50, 200, None, 0, "Common"),
        ("trx_booster_v1", "TRX Booster", "+1.0 Mining Power",
         "mining_speed", 1.0, 300, None, 7, "Rare"),
        ("ultra_miner_v1", "Ultra Miner", "Auto-mine 2.0 TRX per hour",
         "auto_mine", 2.0, 1500, 0.5, 30, "Epic"),
        ("legendary_core", "Legendary Core", "+200 Max Energy & +2.0 Mining Power",
         "energy", 200, 3000, 2.0, 0, "Legendary"),
    ]'''

new_items = '''    default_items = [
        ("starter_miner_v1", "Starter Miner", "Auto-mine 0.15 TRX/hour for 10 days",
         "auto_mine", 0.15, 50, None, 10, "Common"),
        ("standard_miner_v1", "Standard Miner", "Auto-mine 0.3 TRX/hour for 15 days",
         "auto_mine", 0.3, 150, None, 15, "Rare"),
        ("pro_miner_v1", "Pro Miner", "Auto-mine 0.6 TRX/hour for 20 days",
         "auto_mine", 0.6, 400, None, 20, "Epic"),
        ("energy_core_v1", "Energy Core", "+50 Max Energy",
         "energy", 50, 200, None, 0, "Common"),
        ("trx_booster_v1", "TRX Booster", "+1.0 Mining Power",
         "mining_speed", 1.0, 300, None, 7, "Rare"),
        ("legendary_core", "Legendary Core", "+200 Max Energy & +2.0 Mining Power",
         "energy", 200, 3000, 2.0, 0, "Legendary"),
    ]'''

assert old_items in content, "shop items anchor not found"
content = content.replace(old_items, new_items, 1)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("shop items patched")
