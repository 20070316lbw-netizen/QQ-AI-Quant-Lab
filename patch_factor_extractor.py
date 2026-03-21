import re

with open("src/core/multi_factor/factor_extractor.py", "r") as f:
    content = f.read()

# Add as_of_date to extract_raw_factors
content = content.replace(
    'def extract_raw_factors(ticker: str) -> Dict[str, Any]:',
    'def extract_raw_factors(ticker: str, as_of_date: str = None) -> Dict[str, Any]:'
)

# Fix history fetch
replacement = '''        try:
            if as_of_date:
                start_dt = pd.to_datetime(as_of_date) - pd.DateOffset(months=6)
                hist = t.history(start=start_dt.strftime("%Y-%m-%d"), end=as_of_date)
            else:
                hist = t.history(period="6mo")
            if not hist.empty and len(hist) > 10:'''

content = content.replace('''        try:
            hist = t.history(period="6mo")
            if not hist.empty and len(hist) > 10:''', replacement)

with open("src/core/multi_factor/factor_extractor.py", "w") as f:
    f.write(content)
