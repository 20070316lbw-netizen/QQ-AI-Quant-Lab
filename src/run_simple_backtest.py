import os
import json
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

def load_logs(log_file: str):
    records = []
    if not os.path.exists(log_file):
        print(f"Log file not found: {log_file}")
        return records
        
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records

def test_historic_hit_rate(log_file: str, horizon_days: int = 5):
    """
    简易 T+N 离线结算跑批测试 (基于日志决断快照计算 Hit Rate 和 Alpha)
    """
    records = load_logs(log_file)
    if not records:
        return
        
    print(f"Found {len(records)} signal records in log. Starting retroactive backtesting...")
    
    hits = 0
    total_valid = 0
    cumulative_alpha = 0.0

    # 为了减少网络请求，做极其简易的缓存
    _cache = {}

    for record in records:
        ticker = record["ticker"]
        direction = record["direction"]
        confidence = record.get("adjusted_position_strength", record.get("confidence", 0.5))
        # Log 保存的格式如 "2026-02-23T23:13:14.540350Z"
        date_str = record["timestamp"].split("T")[0]
        
        # 将字符串时间转为 datetime，并向后推 horizon_days 寻找对比收盘价
        trade_date = datetime.strptime(date_str, "%Y-%m-%d")
        end_date = trade_date + timedelta(days=horizon_days + 3) # 为节假日留冗余
        
        start_date_str = trade_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")
        
        cache_key = f"{ticker}_{start_date_str}"
        if cache_key not in _cache:
            print(f"  [>] Fetching actual market trace for {ticker} from {start_date_str}")
            try:
                stock = yf.Ticker(ticker)
                df = stock.history(start=start_date_str, end=end_date_str)
                # 使用时区天真的比较
                df.index = df.index.tz_localize(None)
                _cache[cache_key] = df
            except Exception as e:
                print(f"  [X] Failed fetching data: {e}")
                _cache[cache_key] = pd.DataFrame()
                
        df = _cache[cache_key]
        if df.empty or len(df) < 2:
            print(f"  [-] Not enough data points to settle record {record['snapshot_id']}")
            continue
            
        # 假设交易价格为 T=0 的收盘价（通常回测需要 T+1 开盘，在此精简）
        # 假设卖出为 T+N 天的收盘价
        p_entry = df.iloc[0]["Close"]
        
        # 提取 N 个交易日后的价格
        target_idx = min(horizon_days - 1, len(df) - 1)
        p_exit = df.iloc[target_idx]["Close"]
        
        realized_return = (p_exit / p_entry) - 1.0
        
        is_hit = False
        if direction == "BUY" and realized_return > 0:
            is_hit = True
        elif direction == "SELL" and realized_return < 0:
            is_hit = True
        elif direction == "HOLD":
            # 衡量维持原状是对的？如果是震荡行情 (-2% ~ 2%) 算作命中
            if abs(realized_return) < 0.02:
                is_hit = True
                
        if is_hit:
            hits += 1
            
        # PnL (模拟置信度仓位缩放): 若买入，仓位为正；若卖出，为做空仓位（假设有借券）
        position_exposure = confidence if direction == "BUY" else (-confidence if direction == "SELL" else 0)
        pnl = position_exposure * realized_return
        cumulative_alpha += pnl
        total_valid += 1
        
        print(f"  {ticker} @ {date_str} [{direction} {confidence:.2f}] -> "
              f"Actual:{realized_return:.2%}, Hit:{is_hit}, PnL:{pnl:.2%}")
              
    if total_valid > 0:
        win_rate = hits / total_valid
        print("-" * 50)
        print(f"BACKTEST REPORT:")
        print(f"Signal Evaluated: {total_valid} / {len(records)}")
        print(f"Overall Hit Rate: {win_rate:.2%}")
        print(f"Cumulative Model Alpha: {cumulative_alpha:.2%}")
    else:
        print("No valid signals could be backtested (maybe too recent for T+N data).")

if __name__ == "__main__":
    today = datetime.now().strftime("%Y-%m-%d")
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    default_log = os.path.join(project_root, "logs", f"decisions_{today}.jsonl")
    
    print("=== Kronos & LLM Hybrid Dual-Track Backtester ===")
    test_historic_hit_rate(default_log)
