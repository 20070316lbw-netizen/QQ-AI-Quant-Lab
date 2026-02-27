import sys
import os
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable
    tqdm.write = print

# 加入系统路径以引入主模块
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from trading_signal import generate_signal
from backtest.config import BACKTEST_CONFIG
from backtest.signal_recorder import SignalRecorder
from backtest.performance_analyzer import analyze_performance

def compute_future_actual_data(ticker: str, date: str, horizon: int):
    """
    计算基于指定日期的未来 N 天真实收益率、真实波动率 (std) 及真实振幅 (High-Low/Close)
    """
    try:
        trade_date = datetime.strptime(date, "%Y-%m-%d")
        end_date = trade_date + timedelta(days=horizon + 10)
        
        stock = yf.Ticker(ticker)
        df = stock.history(start=date, end=end_date.strftime("%Y-%m-%d"))
        
        if df.empty or len(df) < horizon + 1:
            return None, None, None
            
        # 裁剪出确切的 horizon 窗口数据 (含 T 日)
        window_df = df.iloc[:horizon+1]
        
        p_entry = window_df.iloc[0]["Close"]
        p_exit = window_df.iloc[-1]["Close"]
        
        # 指标1：收益率
        actual_return = float((p_exit / p_entry) - 1.0)
        
        # 指标2：真实波动率 (收益率序列的 std)
        daily_returns = window_df["Close"].pct_change().dropna()
        realized_vol = float(daily_returns.std()) if len(daily_returns) > 1 else 0.0
        
        # 指标3：真实振幅 (期间最高 - 期间最低) / 期初
        actual_max = window_df["High"].max()
        actual_min = window_df["Low"].min()
        actual_range_pct = float((actual_max - actual_min) / p_entry)
        
        return actual_return, realized_vol, actual_range_pct
        
    except Exception as e:
        print(f"  [X] Failed fetching actual return for {ticker} at {date}: {e}")
        return None, None, None

def run_backtest():
    universe = BACKTEST_CONFIG["universe"]
    start_date = BACKTEST_CONFIG["start_date"]
    end_date = BACKTEST_CONFIG["end_date"]
    
    recorder = SignalRecorder(BACKTEST_CONFIG["output_dir"])
    
    # 生成全体交易日历 (以 S&P 500 代表或者直接用 yfinance 的 index)
    print("Pre-fetching SPY calendar to determine trading days...")
    spy = yf.Ticker("SPY")
    spy_df = spy.history(start=start_date, end=end_date)
    # yf returned index might have timezone info
    if spy_df.empty:
        print("Failed to fetch trading days. Aborting.")
        return
        
    trading_dates = spy_df.index.tz_localize(None).strftime("%Y-%m-%d").tolist()
    print(f"Found {len(trading_dates)} trading days from {start_date} to {end_date}.")
    
    # 世纪大回测要求：穷尽所有交易日，不丢失一丝波澜。
    sample_dates = trading_dates
    print(f"Selected {len(sample_dates)} sampling dates per stock for backtesting (Expected total: {len(sample_dates) * len(universe)}).")

    all_results = []
    
    for ticker in universe:
        print(f"\n========== Starting Backtest for {ticker} ==========")
        stock_results = []
        
        # 引入进度条
        for date in tqdm(sample_dates, desc=f"Processing {ticker}"):
            # print(f"[*] Processing {ticker} as of {date}...") # 被进度条替代
            
            try:
                # 1. 挂钩历史断点获取信号 (杜绝未来函数)
                signal = generate_signal(ticker=ticker, as_of_date=date)
                
                # 2. 拉取真正未来收益、波幅用于验证 Z-Score 的预测力量
                fut_ret_1d, fut_vol_1d, fut_range_1d = compute_future_actual_data(ticker, date, horizon=1)
                fut_ret_5d, fut_vol_5d, fut_range_5d = compute_future_actual_data(ticker, date, horizon=5)
                
                if fut_ret_1d is None or fut_ret_5d is None:
                    print(f"  [-] Skipping {date} due to lack of future return data.")
                    continue
                    
                # 3. 构造落盘用的大宽表数据 (纳入 Phase 6 延伸矩阵)
                meta = signal.get("metadata", {})
                
                record = {
                    "date": date,
                    "ticker": ticker,
                    "regime": signal.get("regime", "UNKNOWN"),
                    "z_score": signal.get("z_score", 0.0),
                    "regime_strength": signal.get("regime_strength", 0.0),
                    "direction": signal["direction"],
                    "mean_return": signal["mean_return"],
                    "uncertainty": signal["uncertainty"],
                    "predicted_range_pct": signal.get("predicted_range_pct", 0.0),
                    "adjusted_position_strength": signal["adjusted_position_strength"],
                    "sentiment_score": meta.get("sentiment_score", 0.0),
                    "risk_factor": meta.get("risk_factor", 0.0),
                    "future_return_1d": fut_ret_1d,
                    "realized_vol_1d": fut_vol_1d,
                    "actual_range_1d": fut_range_1d,
                    "future_return_5d": fut_ret_5d,
                    "realized_vol_5d": fut_vol_5d,
                    "actual_range_5d": fut_range_5d
                }
                
                stock_results.append(record)
                all_results.append(record)
                
            except Exception as e:
                # 只在发生异常时打断进度条打印报错
                tqdm.write(f"  [X] Failed processing {ticker} at {date}: {e}")
                
        # 每跑完一只股票的所有日子，进行一次强制落盘 (避免三年来中途崩溃引发的全部白干)。
        if stock_results:
            recorder.save_batch(stock_results)
            
    # 触发硬核分析模块
    print("\n========== Backtest Execution Completed ==========")
    if all_results:
        analyze_performance(recorder.get_latest_file_path())
    else:
        print("No valid results collected.")

if __name__ == "__main__":
    run_backtest()
