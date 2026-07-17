with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

old_line = '''@app.route("/api/nft/mint", methods=["POST"])
def api_nft_mint():
    data = request.json'''

new_line = '''@app.route("/api/nft/mint", methods=["POST"])
def api_nft_mint():
    content_length = request.content_length
    logger.info(f"NFT_MINT_DEBUG raw request received, content_length={content_length}")
    data = request.get_json(silent=True)
    if data is None:
        raw_preview = request.get_data(as_text=True)[:200]
        logger.info(f"NFT_MINT_DEBUG JSON PARSE FAILED, content_length={content_length}, raw_preview={raw_preview}")
        return jsonify({"success": False, "error": "Invalid request body"}), 400'''

assert old_line in content, "nft mint function start anchor not found"
content = content.replace(old_line, new_line, 1)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("main.py patched with deeper NFT mint debug logging")
