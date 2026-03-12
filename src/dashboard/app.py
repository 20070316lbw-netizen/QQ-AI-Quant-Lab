"""
AlphaRanker Data Explorer (v2)
==============================
文件浏览器式仪表盘 — 支持目录树导航、K线图、财报表格、数据预览。

启动: python dashboard/app.py
访问: http://localhost:5000
"""
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from flask import Flask, render_template, jsonify, request
import pandas as pd
import glob
import json
import pickle

app = Flask(__name__, template_folder='templates', static_folder='static')

DATA_ROOT = r'C:\Data\Market'
# Also scan legacy paths for data still being fetched
LEGACY_DATA = r'C:\AlphaRanker\data'


def build_tree(root_path, rel=""):
    """递归构建目录树 JSON"""
    result = []
    if not os.path.exists(root_path):
        return result
    try:
        entries = sorted(os.listdir(root_path))
    except PermissionError:
        return result

    for entry in entries:
        full = os.path.join(root_path, entry)
        node_path = (rel + "/" + entry) if rel else entry

        if os.path.isdir(full):
            children = build_tree(full, node_path)
            file_count = sum(1 for c in children if c.get("type") == "file")
            dir_count = sum(1 for c in children if c.get("type") == "dir")
            # Count all files recursively
            total_files = 0
            for c in children:
                if c.get("type") == "file":
                    total_files += 1
                elif c.get("type") == "dir":
                    total_files += c.get("totalFiles", 0)

            result.append({
                "name": entry,
                "path": node_path,
                "type": "dir",
                "children": children[:200],  # cap for large dirs
                "totalFiles": total_files,
                "truncated": len(children) > 200,
            })
        elif entry.endswith('.parquet'):
            size = os.path.getsize(full)
            result.append({
                "name": entry,
                "path": node_path,
                "type": "file",
                "size": size,
                "sizeStr": f"{size/1024:.0f}KB" if size < 1048576 else f"{size/1048576:.1f}MB",
            })
    return result


def resolve_path(rel_path):
    """将相对路径解析为绝对路径，优先新数据中心，fallback 到旧路径"""
    rel_path = rel_path.replace("/", os.sep)
    p = os.path.join(DATA_ROOT, rel_path)
    if os.path.exists(p):
        return p
    # Legacy fallback: strip 'cn/' or 'us/' prefix and map to old dirs
    legacy_map = {
        "cn" + os.sep + "prices": os.path.join(LEGACY_DATA, "prices"),
        "cn" + os.sep + "fundamentals": os.path.join(LEGACY_DATA, "fundamentals"),
        "us" + os.sep + "prices": os.path.join(LEGACY_DATA, "us_prices"),
        "us" + os.sep + "fundamentals": os.path.join(LEGACY_DATA, "us_fundamentals"),
    }
    for prefix, legacy_dir in legacy_map.items():
        if rel_path.startswith(prefix + os.sep):
            fname = rel_path[len(prefix)+1:]
            p2 = os.path.join(legacy_dir, fname)
            if os.path.exists(p2):
                return p2
    p2 = os.path.join(LEGACY_DATA, rel_path)
    if os.path.exists(p2):
        return p2
    return p


def read_parquet_safe(path, max_rows=100):
    """安全读取 parquet"""
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_parquet(path)
        # Flatten MultiIndex columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] if col[1] == '' else f"{col[0]}" for col in df.columns]
            df = df.loc[:, ~df.columns.duplicated()]
        # Date index
        if isinstance(df.index, pd.DatetimeIndex):
            df.index = df.index.strftime("%Y-%m-%d")
        if "ticker" in df.columns:
            df = df.drop(columns=["ticker"])
        df = df.fillna(0)
        total_rows = len(df)
        df = df.head(max_rows)
        return {
            "columns": df.columns.tolist(),
            "index": df.index.tolist(),
            "data": df.values.tolist(),
            "totalRows": total_rows,
            "shape": [total_rows, len(df.columns)],
        }
    except Exception as e:
        return {"error": str(e)}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/tree")
def api_tree():
    """返回完整目录树"""
    tree = []
    # New data center
    if os.path.exists(DATA_ROOT):
        tree = build_tree(DATA_ROOT)
    # Also include legacy data still being fetched
    legacy_items = build_tree(LEGACY_DATA)
    if legacy_items:
        tree.append({
            "name": "(legacy - fetching)",
            "path": "_legacy",
            "type": "dir",
            "children": legacy_items,
            "totalFiles": sum(c.get("totalFiles", 0) if c["type"]=="dir" else 1 for c in legacy_items),
        })
    return jsonify(tree)


@app.route("/api/preview")
def api_preview():
    """预览任意 parquet 文件"""
    rel = request.args.get("path", "")
    path = resolve_path(rel)
    data = read_parquet_safe(path, max_rows=50)
    if data is None:
        return jsonify({"error": "File not found"})
    
    # Add stats
    try:
        df = pd.read_parquet(path)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]
            df = df.loc[:, ~df.columns.duplicated()]
        if "ticker" in df.columns:
            df = df.drop(columns=["ticker"])
        numeric_cols = df.select_dtypes(include='number')
        if not numeric_cols.empty:
            stats = numeric_cols.describe().round(2).to_dict()
            data["stats"] = stats
    except:
        pass

    return jsonify(data)


@app.route("/api/candlestick")
def api_candlestick():
    """返回 K 线数据 (OHLCV)"""
    rel = request.args.get("path", "")
    path = resolve_path(rel)
    if not os.path.exists(path):
        return jsonify({"error": "Not found"})

    try:
        df = pd.read_parquet(path)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]
            df = df.loc[:, ~df.columns.duplicated()]
        if isinstance(df.index, pd.DatetimeIndex):
            df.index = df.index.strftime("%Y-%m-%d")

        # Map column names (case insensitive)
        col_map = {}
        for c in df.columns:
            cl = c.lower()
            if cl in ('open',): col_map['open'] = c
            elif cl in ('high',): col_map['high'] = c
            elif cl in ('low',): col_map['low'] = c
            elif cl in ('close',): col_map['close'] = c
            elif cl in ('volume',): col_map['volume'] = c

        if 'close' not in col_map:
            return jsonify({"error": "No OHLC columns"})

        # Downsample for large datasets
        step = max(1, len(df) // 500)
        df = df.iloc[::step]

        result = {"dates": df.index.tolist()}
        for key in ['open', 'high', 'low', 'close', 'volume']:
            if key in col_map:
                result[key] = pd.to_numeric(df[col_map[key]], errors='coerce').fillna(0).tolist()

        # MA lines
        if 'close' in col_map:
            close_s = pd.to_numeric(df[col_map['close']], errors='coerce')
            result['ma5'] = close_s.rolling(5, min_periods=1).mean().fillna(0).tolist()
            result['ma20'] = close_s.rolling(20, min_periods=1).mean().fillna(0).tolist()

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)})


@app.route("/api/industry_dist")
def api_industry_dist():
    """行业分布统计"""
    rel = request.args.get("path", "")
    path = resolve_path(rel)
    if not os.path.exists(path):
        return jsonify({"error": "Not found"})
    try:
        df = pd.read_parquet(path)
        if 'industry_name' in df.columns:
            dist = df['industry_name'].value_counts().to_dict()
        elif 'sector' in df.columns:
            dist = df['sector'].value_counts().to_dict()
        else:
            dist = {}
        return jsonify(dist)
    except Exception as e:
        return jsonify({"error": str(e)})


# ─── Data Slicer APIs ───

def _get_fund_dirs(market, report_type):
    """获取财报目录和文件模式"""
    dirs = []
    if market == 'us':
        suffix_map = {'income': '_income.parquet', 'balance': '_balance.parquet', 'cashflow': '_cashflow.parquet'}
        suffix = suffix_map.get(report_type, '_income.parquet')
        for d in [os.path.join(DATA_ROOT, 'us', 'fundamentals'), os.path.join(LEGACY_DATA, 'us_fundamentals')]:
            if os.path.exists(d):
                dirs.append((d, f"*{suffix}"))
    else:
        for d in [os.path.join(DATA_ROOT, 'cn', 'fundamentals'), os.path.join(LEGACY_DATA, 'fundamentals')]:
            if os.path.exists(d):
                dirs.append((d, "*_fundamental.parquet"))
    return dirs


@app.route("/api/slicer/fields")
def api_slicer_fields():
    """获取可用字段列表 — 从第一个文件中读取列名"""
    market = request.args.get("market", "us")
    report_type = request.args.get("type", "income")
    dirs = _get_fund_dirs(market, report_type)

    for d, pattern in dirs:
        files = glob.glob(os.path.join(d, pattern))
        if files:
            try:
                df = pd.read_parquet(files[0])
                cols = [c for c in df.columns if c != 'ticker']
                return jsonify({"fields": cols, "count": len(files)})
            except:
                continue
    return jsonify({"fields": [], "count": 0})


@app.route("/api/slicer/extract")
def api_slicer_extract():
    """跨股票提取指定字段并拼接"""
    market = request.args.get("market", "us")
    report_type = request.args.get("type", "income")
    field = request.args.get("field", "")
    if not field:
        return jsonify({"error": "Missing field parameter"})

    dirs = _get_fund_dirs(market, report_type)
    rows = []

    for d, pattern in dirs:
        files = sorted(glob.glob(os.path.join(d, pattern)))
        for f in files:
            try:
                df = pd.read_parquet(f)
                if field not in df.columns:
                    continue
                # Extract ticker from filename
                basename = os.path.basename(f)
                if market == 'us':
                    ticker = basename.split('_')[0]
                else:
                    ticker = basename.replace('_fundamental.parquet', '')

                series = df[field]
                if isinstance(df.index, pd.DatetimeIndex):
                    dates = df.index.strftime("%Y-%m-%d").tolist()
                else:
                    dates = [str(x) for x in df.index.tolist()]

                values = pd.to_numeric(series, errors='coerce').fillna(0).tolist()
                rows.append({"ticker": ticker, "dates": dates, "values": values})
            except:
                continue

    # Build pivot table: rows=tickers, cols=dates
    all_dates = sorted(set(d for r in rows for d in r["dates"]), reverse=True)
    table_data = []
    for r in rows:
        date_map = dict(zip(r["dates"], r["values"]))
        row_vals = [date_map.get(d, 0) for d in all_dates]
        table_data.append({"ticker": r["ticker"], "values": row_vals})

    return jsonify({
        "field": field,
        "dates": all_dates,
        "data": table_data,
        "totalStocks": len(table_data),
    })


@app.route("/api/slicer/csv")
def api_slicer_csv():
    """导出切片数据为 CSV"""
    from flask import Response
    import io

    market = request.args.get("market", "us")
    report_type = request.args.get("type", "income")
    field = request.args.get("field", "")
    if not field:
        return Response("Missing field", status=400)

    # Reuse extraction logic
    dirs = _get_fund_dirs(market, report_type)
    rows = []
    for d, pattern in dirs:
        files = sorted(glob.glob(os.path.join(d, pattern)))
        for f in files:
            try:
                df = pd.read_parquet(f)
                if field not in df.columns:
                    continue
                basename = os.path.basename(f)
                if market == 'us':
                    ticker = basename.split('_')[0]
                else:
                    ticker = basename.replace('_fundamental.parquet', '')
                series = df[field]
                if isinstance(df.index, pd.DatetimeIndex):
                    dates = df.index.strftime("%Y-%m-%d").tolist()
                else:
                    dates = [str(x) for x in df.index.tolist()]
                values = pd.to_numeric(series, errors='coerce').fillna(0).tolist()
                rows.append({"ticker": ticker, "dates": dates, "values": values})
            except:
                continue

    all_dates = sorted(set(d for r in rows for d in r["dates"]), reverse=True)

    # Build CSV
    buf = io.StringIO()
    buf.write("Ticker," + ",".join(all_dates) + "\n")
    for r in rows:
        date_map = dict(zip(r["dates"], r["values"]))
        vals = [str(date_map.get(d, 0)) for d in all_dates]
        buf.write(r["ticker"] + "," + ",".join(vals) + "\n")

    csv_content = buf.getvalue()
    filename = f"slicer_{market}_{report_type}_{field}.csv"
    return Response(
        csv_content,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@app.route("/api/stats")
def api_stats():
    """数据统计"""
    def count_files(d, pattern="*.parquet"):
        if not os.path.exists(d): return 0
        return len(glob.glob(os.path.join(d, pattern)))

    cn_p = os.path.join(DATA_ROOT, 'cn', 'prices')
    cn_f = os.path.join(DATA_ROOT, 'cn', 'fundamentals')
    cn_f_legacy = os.path.join(LEGACY_DATA, 'fundamentals')
    us_p = os.path.join(DATA_ROOT, 'us', 'prices')
    us_p_legacy = os.path.join(LEGACY_DATA, 'us_prices')
    us_f = os.path.join(DATA_ROOT, 'us', 'fundamentals')
    us_f_legacy = os.path.join(LEGACY_DATA, 'us_fundamentals')

    return jsonify({
        "cn_prices": count_files(cn_p),
        "cn_fundamentals": count_files(cn_f) + count_files(cn_f_legacy),
        "us_prices": count_files(us_p) + count_files(us_p_legacy),
        "us_fundamentals": count_files(us_f, "*_income*") + count_files(us_f_legacy, "*_income*"),
    })


@app.route("/api/model/signals")
def api_model_signals():
    """模型打分信号：加载最新特征 + LightGBM 模型 + 静态基本面数据进行融合"""
    market = request.args.get("market", "us")
    if market != "us":
        return jsonify({"error": "Currently only US model is available"})
        
    features_path = os.path.join(DATA_ROOT, 'us', 'us_features.parquet')
    model_path = os.path.join(os.path.dirname(__file__), '..', '..', 'models', 'us_stock', 'us_lgbm.pkl')
    info_path = os.path.join(DATA_ROOT, 'us', 'fundamentals', 'us_stock_info.parquet')
    
    if not os.path.exists(features_path) or not os.path.exists(model_path):
        return jsonify({"error": "Model or Features not found. Please train first."})
        
    try:
        # Load model
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        model = model_data['model']
        valid_feats = model_data['features']
        
        # Load latest features
        df = pd.read_parquet(features_path)
        latest_date = df['report_date'].max()
        df_latest = df[df['report_date'] == latest_date].copy()
        
        # Check if all features exist
        for col in valid_feats:
            if col not in df_latest.columns:
                df_latest[col] = 0.0
                
        X = df_latest[valid_feats].fillna(0).values
        preds = model.predict(X)
        df_latest['score'] = preds
        
        # Sort by score
        df_latest = df_latest.sort_values('score', ascending=False)
        df_latest['rank'] = range(1, len(df_latest) + 1)
        
        # Merge basic fundamentals for filtering (PE, Mkt Cap, Sector)
        base_cols = ['ticker', 'score', 'rank', 'mom_6m', 'vol_60d']
        for col in valid_feats:
            if col not in base_cols:
                base_cols.append(col)
                
        out_df = df_latest[base_cols].copy()
        
        if os.path.exists(info_path):
            info = pd.read_parquet(info_path)
            # info contains: marketCap, trailingPE, forwardPE, priceToBook, sector, industry...
            out_df = out_df.merge(info, on='ticker', how='left')
            
        out_df = out_df.fillna({
            'trailingPE': -1, 'forwardPE': -1, 'priceToBook': -1, 'marketCap': 0, 'sector': 'Unknown'
        })
        
        # Convert to records
        results = out_df.to_dict(orient='records')
        
        return jsonify({
            "report_date": str(latest_date)[:10],
            "total_stocks": len(results),
            "data": results
        })
    except Exception as e:
        return jsonify({"error": str(e)})


if __name__ == "__main__":
    print("=" * 50)
    print("  AlphaRanker Data Explorer v2")
    print("  http://localhost:5000")
    print(f"  Data Root: {DATA_ROOT}")
    print("=" * 50)
    app.run(debug=False, port=5000)
