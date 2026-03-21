with open("src/trading_signal.py", "r") as f:
    content = f.read()

content = content.replace(
    '            raw_factors = extract_raw_factors(ticker)',
    '            raw_factors = extract_raw_factors(ticker, as_of_date=as_of_date)'
)

with open("src/trading_signal.py", "w") as f:
    f.write(content)
