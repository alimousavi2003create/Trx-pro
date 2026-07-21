import random

deco_pool = list("+<÷]/,-:!&♤•□◇●$~£■○¡☆《》")

def make_template(idx):
    d = lambda: random.choice(deco_pool)
    styles = [
        f"{d()}{d()} ROUND CLOSED {d()}{d()}\n{{color}} Multiplier: {{mult}}x\n{d()*3} @Minerbyner_bot {d()*3}",
        f"{d()}{d()}{d()} TRX PRO {d()}{d()}{d()}\n{{color}} Closed at {{mult}}x\nJoin: @Minerbyner_bot {d()}",
        f"{d()} CRASH RESULT {d()}\n{{mult}}x {{color}}\n{d()*2} Play now {d()*2} @Minerbyner_bot",
        f"{d()*4}\n{{color}} {{mult}}x {d()}\n{d()*4}\n@Minerbyner_bot",
        f"Round settled {d()}{d()}\n{{color}} {{mult}}x\n{d()} TRX PRO {d()} @Minerbyner_bot",
    ]
    return random.choice(styles)

templates = [make_template(i) for i in range(100)]
with open("message_templates_output.txt", "w", encoding="utf-8") as f:
    for t in templates:
        f.write(repr(t) + ",\n")
print("generated")
