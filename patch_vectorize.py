import os
import numpy as np

# Fix 1: tui_app.py iterrows -> itertuples
with open("src/tui_app.py", "r") as f:
    tui_content = f.read()

tui_content = tui_content.replace(
    'for i, (_, row) in enumerate(top_20.iterrows()):',
    'for i, row in enumerate(top_20.itertuples()):'
)

# Fix getattr for row
tui_content = tui_content.replace(
    "row.get('sp_ratio_rank', 0)",
    "getattr(row, 'sp_ratio_rank', 0)"
)
tui_content = tui_content.replace("row['ticker']", "row.ticker")
tui_content = tui_content.replace("row['alpha_score']", "row.alpha_score")
tui_content = tui_content.replace("row['sp_ratio_rank']", "row.sp_ratio_rank")
tui_content = tui_content.replace("row['mom_60d_rank']", "row.mom_60d_rank")
tui_content = tui_content.replace("row['vol_60d_res_rank']", "row.vol_60d_res_rank")

tui_content = tui_content.replace(
    'for _, row in pts.iterrows():',
    'for row in pts.itertuples():'
)
tui_content = tui_content.replace("row['label_next_month']", "row.label_next_month")

with open("src/tui_app.py", "w") as f:
    f.write(tui_content)

# Fix 2: yuan_500_assistant.py
with open("src/alpharanker/live/yuan_500_assistant.py", "r") as f:
    yuan_content = f.read()

yuan_content = yuan_content.replace(
    'for _, row in top_picks.iterrows():',
    'for row in top_picks.itertuples():'
)
yuan_content = yuan_content.replace("row['raw_close']", "row.raw_close")
yuan_content = yuan_content.replace("row['ticker']", "row.ticker")

with open("src/alpharanker/live/yuan_500_assistant.py", "w") as f:
    f.write(yuan_content)

# Fix 3: Vectorize apply(lambda) for SS/SZ
files_to_fix = [
    "src/alpharanker/eval/eval_cn_ic_decay.py",
    "src/alpharanker/eval/eval_cn_oos_consistency.py",
    "src/alpharanker/eval/backtest_2015_crash.py",
    "src/alpharanker/eval/eval_cn_deep_dive.py"
]

for fp in files_to_fix:
    with open(fp, "r") as f:
        content = f.read()

    # Prepend import numpy as np safely
    if "import numpy as np" not in content:
        content = "import numpy as np\n" + content

    old_line = 'index_map[\'ticker\'] = index_map[\'code\'].apply(lambda x: x.split(".")[1] + (".SS" if x.startswith("sh") else ".SZ"))'
    new_line = 'index_map[\'ticker\'] = index_map[\'code\'].str.split(".").str[1] + np.where(index_map[\'code\'].str.startswith("sh"), ".SS", ".SZ")'

    content = content.replace(old_line, new_line)

    with open(fp, "w") as f:
        f.write(content)
