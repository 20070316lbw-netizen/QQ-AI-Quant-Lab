with open("src/core/factor_engine.py", "r") as f:
    content = f.read()

content = content.replace(
    '    def get_raw_score(ticker: str) -> dict:',
    '    def get_raw_score(ticker: str, as_of_date: str = None) -> dict:'
)

content = content.replace(
    '            raw_factors = extract_raw_factors(ticker)',
    '            raw_factors = extract_raw_factors(ticker, as_of_date)'
)

content = content.replace(
    '    def get_factor_signal(ticker: str) -> dict:',
    '    def get_factor_signal(ticker: str, as_of_date: str = None) -> dict:'
)

content = content.replace(
    '        score_data = FactorEngine.get_raw_score(ticker)',
    '        score_data = FactorEngine.get_raw_score(ticker, as_of_date)'
)

with open("src/core/factor_engine.py", "w") as f:
    f.write(content)
