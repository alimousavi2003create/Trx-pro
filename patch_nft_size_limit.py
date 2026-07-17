with open("config.py", "r", encoding="utf-8") as f:
    content = f.read()

old_line = "NFT_MAX_IMAGE_BYTES = 2 * 1024 * 1024  # 2MB limit for base64 image uploads"
new_line = "NFT_MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5MB limit for base64 image uploads"
assert old_line in content, "NFT_MAX_IMAGE_BYTES line not found in config.py"
content = content.replace(old_line, new_line, 1)

with open("config.py", "w", encoding="utf-8") as f:
    f.write(content)

print("config.py updated: NFT image limit raised to 5MB")
