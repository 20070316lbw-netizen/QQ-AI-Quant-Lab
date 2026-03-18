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
HISTORY_DAYS = 120  # 实战要求的历史窗口
OUTPUT_PATH = os.path.join(CN_DIR, 'kronos_ic_results_refined.parquet')

def get_actual_return(ticker, start_date, end_date):
    """获取指定期间的真实收益率"""
    file_path = os.path.join(PRICE_DIR, f"{ticker}.parquet")
    if not os.path.exists(file_path):
        return None
    try:
        df = pd.read_parquet(file_path)
        # 提取核心价格段
        prices = df[(df.index >= start_date) & (df.index <= end_date)]
        if len(prices) < 2:
            return None
        return (prices['close'].iloc[-1] / prices['close'].iloc[0]) - 1.0
    except:
        return None

def main():
    print("="*80)
    print(f"  Kronos Factor IC Evaluation v2.0 (Refined, Year: {TEST_YEAR})")
    print("  [Fix: No Look-ahead Bias, History={HISTORY_DAYS}d]")
    print("="*80)

    # 1. 加载特征库
    FEATURES_PATH = os.path.join(CN_DIR, 'cn_features_enhanced.parquet')
    if not os.path.exists(FEATURES_PATH):
        print("Features path missing")
        return

    df_feat = pd.read_parquet(FEATURES_PATH)
    df_feat['date'] = pd.to_datetime(df_feat['date'])
    df_2024 = df_feat[df_feat['date'].dt.year == TEST_YEAR].sort_values(['date', 'sp_ratio_rank'], ascending=[True, False])
    
    months = sorted(df_2024['date'].unique())
    results = []
    
    # 2. 逐月动态选股并预测
    for i in range(len(months) - 1):
        curr_month = months[i]
        next_month = months[i+1]
        
        # 核心修复 1: 在循环内部当月选股，避免未来信息
        # 选取当月 sp_ratio_rank 最高的 50 只
        monthly_candidates = df_2024[df_2024['date'] == curr_month].head(SAMPLE_TICKERS_COUNT)
        tickers = monthly_candidates['ticker'].tolist()
        
        print(f"\n>> 正在处理横截面: {curr_month.date()} (Selected {len(tickers)} stocks by SP Ratio Rank)")
        
        for ticker in tqdm(tickers, desc=f"Predicting {curr_month.date()}"):
            file_path = os.path.join(PRICE_DIR, f"{ticker}.parquet")
            if not os.path.exists(file_path): continue
                
            hist_df = pd.read_parquet(file_path)
            # Memory Fix: Ensure strict exclusion of target date (<) to prevent Look-ahead bias
            hist_df = hist_df[hist_df.index < curr_month].tail(HISTORY_DAYS) # 取最后 HISTORY_DAYS 天
            
            if len(hist_df) < 60: continue
                
            try:
                # 调用 Kronos API
                pred_df = predict_market_trend(hist_df, pred_len=20, sample_count=3)
                if pred_df is None: continue
                
                kronos_return = pred_df.attrs.get('mean_return', 0)
                
                # 核心修复 3: 记录模型类型
                # 我们通过检查 predictor 内部状态（虽然 API 隐藏了，但我们可以推断或观察 log）
                # 这里我们假设本地化已修好。为了严格统计，我们可以检查 attrs
                # 实际上 predict_market_trend 内部会 print
                # 我们在 API 里增加一个显式的 model_type 记录会更好。
                # 目前由于不方便改 API，我们记录是否有返回值，且捕获日志中的 Falling back 字符（实际通过捕获 stdout 较难）
                # 我们可以通过预读 _get_predictor() 返回的对象类型来判定
                from kronos.api import _get_predictor
                from kronos.api import StatisticalPredictor
                predictor = _get_predictor()
                model_type = "Statistical" if isinstance(predictor, StatisticalPredictor) else "RealKronos"
                
                # 获取真实收益 (下个月初到下个月末)
                actual_return = get_actual_return(ticker, curr_month, next_month)
                
                if actual_return is not None:
                    results.append({
                        'date': curr_month,
                        'ticker': ticker,
                        'kronos_return': kronos_return,
                        'actual_return': actual_return,
                        'model_type': model_type
                    })
            except Exception as e:
                continue
                
    if not results:
        print("❌ 未产生有效评估结果")
        return

    res_df = pd.DataFrame(results)
    res_df.to_parquet(OUTPUT_PATH)
    print(f"Evaluation completed, results saved to: {OUTPUT_PATH}")

    # 3. 统计分析
    print("\n" + "-"*40)
    print("  Refined Statistical Analysis")
    print("-"*40)
    
    # 模型使用率统计
    counts = res_df['model_type'].value_counts()
    real_rate = counts.get('RealKronos', 0) / len(res_df)
    print(f"真实模型率: {real_rate:.1%} ({counts.to_dict()})")
    
    if real_rate < 0.5:
        print("⚠️ WARNING: Real model usage < 50%. The results may be biased by Statistical Predictor!")
    
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
    t_stat = mean_ic / (std_ic / np.sqrt(len(ics)) + 1e-9)
    
    print(f"样本截面数: {len(ics)}")
    print(f"Mean Rank IC: {mean_ic:.4f}")
    print(f"IC Std: {std_ic:.4f}")
    print(f"T-Stat: {t_stat:.2f}")
    
    if abs(mean_ic) > 0.03 and abs(t_stat) > 1.96:
        print("\nConclusion: Kronos factor has significant prediction value (Weighting recommended)")
    else:
        print("\nConclusion: Kronos factor signal is weak or insignificant (Keep default weights)")

if __name__ == "__main__":
    main()
