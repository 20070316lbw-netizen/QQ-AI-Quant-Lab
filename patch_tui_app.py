with open("src/tui_app.py", "r") as f:
    content = f.read()

content = content.replace("row['raw_close']", "row.raw_close")

with open("src/tui_app.py", "w") as f:
    f.write(content)
