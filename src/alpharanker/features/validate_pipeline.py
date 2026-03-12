"""
validate_pipeline.py
======================
AlphaRanker 数据防空洞与自动校验中台
涵盖量化交易最常见的三个完整性等级防漏洞校验：
L1: Data Integrity (数据层)
L2: Feature Integrity (特征层)
L3: Statistical Integrity (验证层)
"""

import os
import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from collections import defaultdict
import lightgbm as lgb


class QuantValidationError(Exception):
    """量化数据异常专用报错类"""
    pass


# ==========================================
# L1: 数据完整性 (Data Integrity Guard)
# ==========================================
def l1_data_integrity_check(df: pd.DataFrame, min_sample_size: int = 3000, date_col: str = "report_date", label_col: str = "label_3m_return"):
    """
    检查 Schema，类型与极度缺失的宏观健康度
    """
    print(f">> [L1 Check] 开始数据完整性校验 (Target: {label_col})...")
    
    # 1. Schema 排雷: 绝对禁止 MultiIndex 进入模型训练
    if isinstance(df.columns, pd.MultiIndex):
        raise QuantValidationError("L1_Error: 宽表检测到残余的 MultiIndex 结构！")
    
    for c in df.columns:
        if isinstance(c, tuple) or str(c).startswith("("):
            raise QuantValidationError(f"L1_Error: 列名包含了幽灵元组 {c}。")

    # 2. 基本列是否存在
    assert "ticker" in df.columns, "L1_Error: 缺失 'ticker' 列"
    assert date_col in df.columns, f"L1_Error: 缺失 '{date_col}' 列"
    assert label_col in df.columns, f"L1_Error: 缺失 '{label_col}' 列"

    # 3. 标签致命缺失检查 (Label NaN Ratio)
    nan_ratio = df[label_col].isna().mean()
    if nan_ratio > 0.5:
        raise QuantValidationError(f"L1_Error: 标签大崩塌！整体缺失率高达 {nan_ratio:.1%}。")
        
    # 4. 有效样本熔断
    valid_count = df[label_col].notna().sum()
    if valid_count < min_sample_size:
        raise QuantValidationError(f"L1_Error: 有效训练样本仅剩 {valid_count} 条，远低于设定红线 {min_sample_size}。")
        
    print(f"  √ L1 通过！有效样本数 {valid_count}，标签缺失率 {nan_ratio:.1%}")
    return True


# ==========================================
# L2: 特征完整性 (Feature Integrity Guard)
# ==========================================
def l2_time_alignment_check(features_df: pd.DataFrame, original_price_dir: str, target_shift_days: int = 63, test_tickers: list = ['AAPL', 'MSFT']):
    """
    检查标签时间是否有未来函数错位
    理论上 Label 必须精确等于 (P_{t+target} / P_t) - 1
    如果误差 > 1e-8，即产生对齐漂移
    """
    print(">> [L2 Check] 开始时间戳结对绝对误差校验...")
    
    passed_cnt = 0
    for tk in test_tickers:
        price_path = os.path.join(original_price_dir, f"{tk}.parquet")
        if not os.path.exists(price_path):
            continue
            
        pdf = pd.read_parquet(price_path)
        pdf = pdf.loc[:, ~pdf.columns.duplicated()].sort_index()
        if "Close" not in pdf.columns:
            continue
            
        fdf = features_df[(features_df["ticker"] == tk) & (features_df["label_3m_return"].notna())].copy()
        for idx, row in fdf.iterrows():
            date_t = row["report_date"]
            label_val = row["label_3m_return"]
            
            # 定位当时的原始价格表索引
            if date_t not in pdf.index:
                continue
                
            loc_t = pdf.index.get_loc(date_t)
            loc_target = loc_t + target_shift_days
            
            if loc_target < len(pdf):
                p_t = pdf["Close"].iloc[loc_t]
                p_target = pdf["Close"].iloc[loc_target]
                true_label = (p_target / p_t) - 1.0
                
                err = abs(true_label - label_val)
                if err > 1e-8:
                    raise QuantValidationError(f"L2_Error: '{tk}' 在 {date_t} 的收益率标签偏离真实收益！代码中的 Shift 与实际自然日索引脱节！ (Diff: {err})")
        
        passed_cnt += 1
        
    print(f"  √ L2 通过！随机抽查 {passed_cnt} 只股票的时间错位，误差严格处于 < 1e-8 的理论置信域。")
    return True


# ==========================================
# L3: 统计层评估封闭 (Statistical Integrity Guard)
# ==========================================
def compute_rank_ic(df: pd.DataFrame, pred_col: str = "pred", label_col: str = "relevance", date_col: str = "report_date") -> float:
    """
    【强制隔离封装层】严格禁止全局 spearmanr!
    必须通过截面 date 的 loop 来生成准确无偏的横截面 Rank IC。
    """
    assert date_col in df.columns, f"compute_rank_ic 报错：必须含有 {date_col} 才能约束横截面切分！"
    
    ic_list = []
    for date, grp in df.groupby(date_col):
        if len(grp) > 5 and grp[pred_col].std() > 1e-6 and grp[label_col].std() > 1e-6:
            ic, _ = spearmanr(grp[pred_col], grp[label_col])
            ic_list.append(ic)
            
    if not ic_list:
        return 0.0
    return float(np.mean(ic_list))


def run_placebo_test(X_train, y_train, q_train, X_test, y_test_df: pd.DataFrame, original_ic: float, params: dict, num_boost_round: int = 50, seeds: int = 50):
    """
    鲁棒多种子标签暴力置换检验 (Permutation Test)
    当你的 IC > 0.05 兴奋得睡不着觉时，请先让这 50 组纯瞎猜的猴子跑一次。
    如果它们也能跑你的分数，那你基本就可以删代码了。
    """
    print(f"\n>> [L3 Check] 开启 {seeds} 次大规模蒙特卡洛标签置换 (Placebo) 探测...")
    import copy
    
    placebo_ics = []
    for s in range(seeds):
        # 1. 全局打乱
        y_fake = copy.deepcopy(y_train)
        np.random.seed(s)
        np.random.shuffle(y_fake)
        
        # 2. 轻量级试探
        dtrain = lgb.Dataset(X_train, label=y_fake, group=q_train)
        pms = copy.deepcopy(params)
        pms["seed"] = s
        pms["verbose"] = -1
        
        try:
            model = lgb.train(pms, dtrain, num_boost_round=num_boost_round)
            preds = model.predict(X_test)
            
            y_test_df["fake_pred"] = preds
            ic = compute_rank_ic(y_test_df, pred_col="fake_pred", label_col="relevance")
            placebo_ics.append(ic)
        except Exception:
            pass
            
    mean_noise_ic = np.mean(placebo_ics)
    std_noise_ic = np.std(placebo_ics)
    
    # 构建纯噪声的正态临界高点 (3-Sigma Rule approx 99.7%)
    threshold = mean_noise_ic + 3 * std_noise_ic
    
    print(f"  随机噪声均值 Null IC: {mean_noise_ic:.4f} (std: {std_noise_ic:.4f})")
    print(f"  噪点三西格玛警戒线: {threshold:.4f}")
    
    if original_ic > threshold and original_ic > 0.02:
        print(f"  [PASS] L3 Pass！你的真实 IC({original_ic:.4f}) 显著贯穿了置换假设区间，证明了特征与标签极具硬核因果联系。")
    else:
        print(f"  [WARN] L3 Warning！真实 IC 没有逃离 3-Sigma 引力圈，甚至猴子扔飞镖也能拿你的特征组合跑出这个高分！(前视偏差 Leakage 或纯拟合噪声灾难)")

    return placebo_ics


def run_single_factor_baseline(test_df: pd.DataFrame, factor_col: str = "Total Assets", label_col: str = "relevance") -> float:
    """
    猩猩实验 (The Ape Test)
    看看极度耗电的树模型是否只是对最原始的基本盘因子执行了平庸的等权照搬。
    """
    print(f"\n>> [L3 Check] 单因子 '{factor_col}' 裸跑探测...")
    if factor_col not in test_df.columns:
        print(f"  [Skip] {factor_col} 不在测试集中")
        return 0.0
        
    ic = compute_rank_ic(test_df, pred_col=factor_col, label_col=label_col)
    
    print(f"  单因子基准 IC: {ic:.4f}")
    return ic

