with open("src/core/multi_factor/factor_extractor.py", "r") as f:
    content = f.read()

# Remove the zombie factor "price"
content = content.replace(
    '''        # 补充市价等基础信息
        current_price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
        factors["meta"]["price"] = current_price

''',
    ''''''
)

with open("src/core/multi_factor/factor_extractor.py", "w") as f:
    f.write(content)
