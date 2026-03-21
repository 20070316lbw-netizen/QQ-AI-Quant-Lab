with open("src/alpharanker/live/yuan_500_assistant.py", "r") as f:
    content = f.read()

content = content.replace("row['alpha_score']", "row.alpha_score")

with open("src/alpharanker/live/yuan_500_assistant.py", "w") as f:
    f.write(content)
