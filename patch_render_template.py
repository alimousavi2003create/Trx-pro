with open("main.py", "r", encoding="utf-8") as f:
    content = f.read()

old_home = '''@app.route("/")
def home():
    return render_template("index.html")'''
new_home = '''@app.route("/")
def home():
    return render_template("index.html", bot_username=config.BOT_USERNAME)'''
assert old_home in content, "home route anchor not found"
content = content.replace(old_home, new_home, 1)

with open("main.py", "w", encoding="utf-8") as f:
    f.write(content)

print("main.py home route patched successfully")
