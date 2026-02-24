import io
import pandas as pd
from datetime import datetime, timedelta
from crawlers.data_gateway import gateway
from kronos.api import predict_market_trend

class KronosEngine:
    """
    底层数学量化引擎的封装层：负责拉取历史OHLCV数据并驱动基础大语言/统计模型生成预测曲线。
    """
    
    @staticmethod
    def get_raw_prediction(ticker: str, target_date: str, pred_len: int = 30) -> dict:
        """
        获取原始预测数据，不含 LLM 文字解析
        @param target_date: YYYY-MM-DD，预测起点
        @return: {"z_score": float, "expected_return": float, "uncertainty": float}
        """
        try:
            target_dt = datetime.strptime(target_date, "%Y-%m-%d")
            # 出于性能和噪音双重考量，提取最近120天的特征足矣
            start_dt = target_dt - timedelta(days=120)
            start_date_str = start_dt.strftime("%Y-%m-%d")
            # Yfinance end_date 是不包含边界的，需要往后推一天才能取到 target_date 数据
            fetch_end_date = (target_dt + timedelta(days=1)).strftime("%Y-%m-%d")
        except ValueError:
            target_dt = datetime.now()
            start_dt = target_dt - timedelta(days=120)
            start_date_str = start_dt.strftime("%Y-%m-%d")
            fetch_end_date = target_dt.strftime("%Y-%m-%d")
            
        raw_data_str = gateway.get_stock_data(ticker, start_date_str, fetch_end_date)
        
        lines = raw_data_str.strip().split('\n')
        csv_lines = [line for line in lines if not line.startswith('#') and line.strip()]
        
        if not csv_lines or "Error" in raw_data_str or "No data" in raw_data_str:
             raise ValueError(f"Failed to fetch historical data for {ticker}. Detail: {raw_data_str}")
             
        csv_str = '\n'.join(csv_lines)
        df = pd.read_csv(io.StringIO(csv_str), index_col="Date", parse_dates=True)
        
        df.rename(columns={
            "Open": "open", "High": "high", "Low": "low", 
            "Close": "close", "Volume": "volume"
        }, inplace=True)
        
        # 调用底层统一预测接口（基于集成采样，包含 z-score 边界判定逻辑）
        prediction_df = predict_market_trend(df, pred_len=pred_len)
        
        if prediction_df is None or prediction_df.empty:
             raise RuntimeError("Kronos engine returned empty prediction.")
             
        mean_ret = prediction_df.attrs.get('mean_return', 0.0)
        std_ret = prediction_df.attrs.get('std_return', 0.0309)  # 默认降级波动率
        pred_range = prediction_df.attrs.get('predicted_range_pct', 0.0)
        pred_max = prediction_df.attrs.get('predicted_max', 0.0)
        pred_min = prediction_df.attrs.get('predicted_min', 0.0)
        
        # 计算 Regime Strength (原 Z-Score)，设定一个最低噪声地板防止极高杠杆
        noise_floor = 0.005 
        regime_strength = float(mean_ret / max(std_ret, noise_floor))
        
        return {
            "expected_return": float(mean_ret),
            "uncertainty": float(std_ret),
            "z_score": regime_strength,
            "regime_strength": regime_strength,
            "predicted_range_pct": float(pred_range),
            "predicted_max": float(pred_max),
            "predicted_min": float(pred_min)
        }

