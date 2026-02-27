import sys
import os
import yfinance as yf
import datetime
import json

curr_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.abspath(os.path.join(curr_dir, "../.."))
if src_dir not in sys.path:
    sys.path.append(src_dir)

from src.trading_signal import generate_signal

class GridGenerator:
    """
    全天候网格交易计算器 (Grid Array Generator)
    结合 Kronos 的极值预测（Range），为震荡市提供高抛低吸的机械化挂单挂牌。
    """
    
    @staticmethod
    def generate_grid(ticker: str, grid_lines: int = 5, as_of_date: str = None) -> dict:
        """
        生成一整套网格区间
        网格级数默认为 5 档 (即上下各分档)
        """
        ticker = ticker.strip().upper()
        try:
            signal = generate_signal(ticker, as_of_date=as_of_date)
            
            # 获取最新现货收盘价作为基准 P0
            dt = as_of_date if as_of_date else datetime.datetime.now().strftime("%Y-%m-%d")
            end_dt = datetime.datetime.strptime(dt, "%Y-%m-%d")
            start_dt = end_dt - datetime.timedelta(days=10) # 获取近10天确保能拿到最后一日收盘
            
            hist = yf.Ticker(ticker).history(start=start_dt.strftime("%Y-%m-%d"), end=(end_dt + datetime.timedelta(days=1)).strftime("%Y-%m-%d"))
            if hist.empty:
                return {"error": f"无法获取 {ticker} 的现货历史价格作为网格基准。"}
                
            p0 = hist['Close'].iloc[-1]
            
            # Kronos 给出的上下沿保护框 (基于 % 幅度)
            pred_max_pct = signal['predicted_max']
            pred_min_pct = signal['predicted_min']
            
            # 绝对价格极值
            p_max = p0 * (1 + pred_max_pct)
            p_min = p0 * (1 + pred_min_pct)
            
            # 只有在动量弱 (Z-Score 低) 或行情显示震荡时，网格才有最大化收益，趋势市网格会导致单边踏空或套牢
            is_suitable_for_grid = False
            regime = signal['regime']
            z_score = signal['z_score']
            if "RANGING" in regime or abs(z_score) < 1.0:
                is_suitable_for_grid = True
                
            # 切分网格 (从 p_max 到底 p_min，等分为 grid_lines 份)
            grid_step = (p_max - p_min) / max(1, grid_lines)
            levels = []
            
            current_level = p_max
            for i in range(grid_lines + 1):
                action = "SELL (高抛)" if current_level > p0 else "BUY (低吸)"
                if abs(current_level - p0) < grid_step * 0.5:
                    action = "基准轴 (中性持有)"
                    
                levels.append({
                    "level_index": i,
                    "price": round(current_level, 3),
                    "action": action,
                    "distance_from_p0": round((current_level - p0) / p0 * 100, 2)
                })
                current_level -= grid_step
                
            return {
                "ticker": ticker,
                "base_price": round(p0, 3),
                "predicted_high": round(p_max, 3),
                "predicted_low": round(p_min, 3),
                "is_suitable_for_grid": is_suitable_for_grid,
                "regime": regime,
                "grid_levels": levels
            }
                
        except Exception as e:
            return {"error": str(e)}

if __name__ == "__main__":
    out = GridGenerator.generate_grid("AAPL", grid_lines=6)
    print(json.dumps(out, indent=2, ensure_ascii=False))
