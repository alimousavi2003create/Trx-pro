with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

old_items = '''    default_items = [
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
        ("speed_chip_v1", "Speed Chip", "+0.5 Mining Power",
         "mining_speed", 0.5, 150, None, 3, "Common"),
        ("power_core_v1", "Power Core", "+2.0 Mining Power",
         "mining_speed", 2.0, 800, None, 10, "Rare"),
        ("quantum_drill_v1", "Quantum Drill", "+5.0 Mining Power",
         "mining_speed", 5.0, 3000, 1.0, 21, "Epic"),
        ("smart_miner_v1", "Smart Miner", "Auto-mine 1.0 TRX per hour",
         "auto_mine", 1.0, 900, None, 30, "Rare"),
        ("energy_cell_v1", "Energy Cell", "+100 Max Energy",
         "energy", 100, 800, None, 0, "Rare"),
    ]'''
assert old_items in content, "default_items anchor not found (v2)"
content = content.replace(old_items, new_items, 1)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("main.py new items patch (v2) applied successfully")
