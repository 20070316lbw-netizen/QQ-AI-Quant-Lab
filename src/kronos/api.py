"""
Kronos 本地预测 API
====================
将底层复杂的 Transformer 预测模型包装为一个干净简洁的纯函数，
供顶层智能体 (Agent) 和 CLI 直接调用。

用法：
    from kronos.api import predict_market_trend
    prediction_df = predict_market_trend(historical_df, pred_len=30)
"""

import pandas as pd
import numpy as np
from datetime import timedelta
import torch
import warnings

# 屏蔽模型加载可能产生的一些权重不匹配等日志
warnings.filterwarnings('ignore', category=UserWarning)

# 全局缓存储存实例化后的模型，避免重复加载
_kronos_predictor = None

def _get_predictor():
    """懒加载 KronosPredictor 实例"""
    global _kronos_predictor
    if _kronos_predictor is None:
        try:
            from kronos.model.kronos import Kronos, KronosTokenizer, KronosPredictor
            
            # 使用 huggingface_hub 中的类方法动态获取配置和加载权重
            # 注意：实际生产环境中可能需要将这部分硬编码指向本地权重，
            # 这里按照原版 webui 的逻辑使用自动拉取或默认配置
            print("[Kronos] Initializing prediction model (this might take a few seconds)...")
            
            # TODO: 暂时使用默认小参数初始化一个壳，或者应当使用 from_pretrained
            # 原本项目通过 huggingface 拉取 `Alibaba-NLP/kronos-7b` 一类的模型，
            # 由于在无UI模式下，我们需要用户预先下载或通过此处自动下载。
            # 为了 API 简洁性，我们假设用户环境已准备妥当。
            
            tokenizer = KronosTokenizer.from_pretrained("Alibaba-NLP/kronos-7b")
            model = Kronos.from_pretrained("Alibaba-NLP/kronos-7b")
            
            device = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
            _kronos_predictor = KronosPredictor(model, tokenizer, device=device)
            print("[Kronos] Model loaded successfully.")
            
        except Exception as e:
            print(f"[Kronos] Error loading model: {e}")
            raise
            
    return _kronos_predictor


def predict_market_trend(
    df: pd.DataFrame, 
    pred_len: int = 30,
    temperature: float = 1.0,
    top_p: float = 0.9,
    sample_count: int = 1
) -> pd.DataFrame:
    """
    接收历史 K 线数据，输出未来预测走势。
    
    Args:
        df: 历史数据 DataFrame，必须包含 ['open', 'high', 'low', 'close']，可以包含 'volume', 'amount'
        pred_len: 预测未来多少个时间步
        temperature: 采样温度，越高代表预测越具有多样性（但也可能偏离过大）
        top_p: Nucleus 采样率
        sample_count: 采样次数，函数内部会平均这些结果以获得更平滑的预测
        
    Returns:
        pd.DataFrame: 包含未来 pred_len 步开高低收和成交量的预测数据框，索引为未来的日期。
    """
    
    if df.empty:
        raise ValueError("Provided historical data DataFrame is empty.")
        
    # 确保索引是 datetime
    if not isinstance(df.index, pd.DatetimeIndex):
        try:
            df.index = pd.to_datetime(df.index)
        except Exception:
            raise ValueError("DataFrame index must be convertible to DatetimeIndex.")
            
    predictor = _get_predictor()
    
    # 准备时间戳
    x_timestamps = df.index
    
    # 根据历史数据的频率（例如每日）生成未来的时间戳
    # 假设每日数据
    last_date = df.index[-1]
    y_timestamps = pd.date_range(start=last_date + timedelta(days=1), periods=pred_len, freq='B') # 'B' for business days
    
    print(f"[Kronos] Predicting next {pred_len} steps from {last_date.date()}...")
    
    # 调用底层模型的方法
    prediction_df = predictor.predict(
        df=df,
        x_timestamp=x_timestamps,
        y_timestamp=y_timestamps,
        pred_len=pred_len,
        T=temperature,
        top_p=top_p,
        sample_count=sample_count,
        verbose=False # 关闭进度条防止污染 CLI
    )
    
    return prediction_df
