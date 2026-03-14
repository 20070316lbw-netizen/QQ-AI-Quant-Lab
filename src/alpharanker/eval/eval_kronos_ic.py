import os
import sys
import pandas as pd
import numpy as np
from tqdm import tqdm
from scipy.stats import spearmanr, t

# 增加搜索路径
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from config import CN_DIR, PRICE_DIR
from kronos.api import predict_market_trend

# 配置
TEST_YEAR = 2024
SAMPLE_TICKERS_COUNT = 50
OUTPUT_PATH = os.path.join(CN_DIR, 'kronos_ic_results.parquet')

def get_actual_return(ticker, start_date, end_date):
    """获取指定期间的真实收益率"""
    file_path = os.path.join(PRICE_DIR, f"{ticker}.parquet")
    if not os.path.exists(file_path):
        return None
    try:
        df = pd.read_parquet(file_path)
        # 获取最接近 start_date 和 end_date 的收盘价
        prices = df[(df.index >= start_date) & (df.index <= end_date)]
        if len(prices) < 2:
            return None
        return (prices['close'].iloc[-1] / prices['close'].iloc[0]) - 1.0
    except:
        return None

def main():
    print("="*80)
    print(f"  Kronos Factor IC Evaluation (Year: {TEST_YEAR})")
    print("="*80)

    # 1. 加载特征库以获取 2024 年可选股票列表
    FEATURES_PATH = os.path.join(CN_DIR, 'cn_features_enhanced.parquet')
    if not os.path.exists(FEATURES_PATH):
        print("❌ 特征库缺失")
        return

    df_feat = pd.read_parquet(FEATURES_PATH)
    df_feat['date'] = pd.to_datetime(df_feat['date'])
    df_2024 = df_feat[df_feat['date'].dt.year == TEST_YEAR]
    
    if df_2024.empty:
        print("⚠️ 2024 年数据不足")
        return

    # 选取 50 只样本股 (简单选取出现频率最高的，通常代表流动性较好)
    tickers = df_2024['ticker'].value_counts().head(SAMPLE_TICKERS_COUNT).index.tolist()
    months = sorted(df_2024['date'].unique())
    
    results = []
    
    # 2. 循环各个月份执行预测
    for i in range(len(months) - 1):
        curr_month = months[i]
        next_month = months[i+1]
        print(f"\n>> 正在处理横截面: {curr_month.date()}")
        
        for ticker in tqdm(tickers, desc=f"Predicting {curr_month.date()}"):
            # 获取历史数据 (Kronos 需要历史序列)
            file_path = os.path.join(PRICE_DIR, f"{ticker}.parquet")
            if not os.path.exists(file_path):
                continue
                
            hist_df = pd.read_parquet(file_path)
            hist_df = hist_df[hist_df.index <= curr_month].tail(100) # 取最后100天
            
            if len(hist_df) < 50:
                continue
                
            try:
                # 调用 Kronos API
                pred_df = predict_market_trend(hist_df, pred_len=20, sample_count=3)
                if pred_df is None: continue
                
                kronos_return = pred_df.attrs.get('mean_return', 0)
                
                # 获取真实收益 (下个月初到下个月末)
                actual_return = get_actual_return(ticker, curr_month, next_month)
                
                if actual_return is not None:
                    results.append({
                        'date': curr_month,
                        'ticker': ticker,
                        'kronos_return': kronos_return,
                        'actual_return': actual_return
                    })
            except Exception as e:
                # print(f"Error for {ticker}: {e}")
                continue
                
    if not results:
        print("❌ 未产生有效评估结果")
        return

    res_df = pd.DataFrame(results)
    res_df.to_parquet(OUTPUT_PATH)
    print(f"\n✅ 评估完成，结果已保存至: {OUTPUT_PATH}")

    # 3. 计算 IC 与 T-Stat
    print("\n" + "-"*40)
    print("  统计分析结果")
    print("-"*40)
    
    ics = []
    for date, group in res_df.groupby('date'):
        if len(group) > 5:
            ic, _ = spearmanr(group['kronos_return'], group['actual_return'])
            ics.append(ic)
            
    if not ics:
        print("数据量不足以计算月度 IC")
        return
        
    mean_ic = np.mean(ics)
    std_ic = np.std(ics)
    t_stat = mean_ic / (std_ic / np.sqrt(len(ics)))
    
    print(f"样本截面数: {len(ics)}")
    print(f"Mean Rank IC: {mean_ic:.4f}")
    print(f"IC Std: {std_ic:.4f}")
    print(f"T-Stat: {t_stat:.2f}")
    
    if abs(mean_ic) > 0.03 and abs(t_stat) > 1.96:
        print("\n📈 结论: Kronos 因子具有显著的预测增量 (值得加权)")
    else:
        print("\n📉 结论: Kronos 因子信号微弱或不显著 (建议保持原有权重)")

if __name__ == "__main__":
    main()
