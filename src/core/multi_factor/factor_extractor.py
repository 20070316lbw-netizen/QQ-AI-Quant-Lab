import yfinance as yf
import pandas as pd
from typing import Dict, Any

def extract_raw_factors(ticker: str) -> Dict[str, Any]:
    """
    提取基于 Fama-French 及拓展的经典多因子体系裸数据。
    包含：
    1. Value (价值)
    2. Quality (质量)
    3. Size (规模/小盘)
    4. Momentum (动量)
    5. Volatility (波动)
    """
    factors = {
        "value": {"pe_ratio": None, "pb_ratio": None},
        "quality": {"current_ratio": None, "debt_to_equity": None, "profit_margin": None, "roe": None},
        "size": {"market_cap": None},
        "momentum": {"6m_return": None},
        "volatility": {"beta": None},
        "meta": {"is_valid": False, "price": None}
    }
    
    try:
        t = yf.Ticker(ticker.upper())
        info = t.info
        
        if not info or 'symbol' not in info:
            return factors
            
        factors["meta"]["is_valid"] = True
        
        # 补充市价等基础信息
        current_price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose")
        factors["meta"]["price"] = current_price
            
        # 1. 价值因子 (Value)
        # 用市盈率 (PE) 和 市净率 (PB) 作为核心指标
        factors["value"]["pe_ratio"] = info.get("trailingPE") or info.get("forwardPE")
        factors["value"]["pb_ratio"] = info.get("priceToBook")
        
        # 2. 质量因子 (Quality)
        # 健康的造血能力和低危的资产负债表
        factors["quality"]["current_ratio"] = info.get("currentRatio")
        
        # YFinance debtToEquity 返回的是百分比 (例如 150 表示 1.5 倍)
        de = info.get("debtToEquity")
        factors["quality"]["debt_to_equity"] = (de / 100.0) if de is not None else None
        
        factors["quality"]["profit_margin"] = info.get("profitMargins")
        factors["quality"]["roe"] = info.get("returnOnEquity")
        
        # 3. 规模因子 (Size)
        # 总市值 (Market Cap)
        factors["size"]["market_cap"] = info.get("marketCap")
        
        # 4. 波动因子 (Volatility - Low Volatility Factor)
        # 选用相对大盘 Beta
        factors["volatility"]["beta"] = info.get("beta")
        
        # 5. 动量因子 (Momentum - Medium/Long Term)
        # 获取 6 个月的动量收益率 (使用历史截面数据估算)
        try:
            hist = t.history(period="6mo")
            if not hist.empty and len(hist) > 10:
                first_close = hist['Close'].iloc[0]
                last_close = hist['Close'].iloc[-1]
                if first_close > 0:
                    factors["momentum"]["6m_return"] = (last_close - first_close) / first_close
        except Exception as e:
            print(f"[Factor Extractor] 警告: 动量获取失败 {ticker} - {e}")
            
    except Exception as e:
        print(f"[Factor Extractor] 严重错误，抓取 {ticker} 多因子异常: {e}")
        
    return factors

if __name__ == "__main__":
    # 局部测试
    import json
    res = extract_raw_factors("AAPL")
    print(json.dumps(res, indent=2, ensure_ascii=False))
