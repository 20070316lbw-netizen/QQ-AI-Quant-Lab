import yfinance as yf
import pandas as pd
import os
import json

def fetch_extreme_event_data():
    """
    爬取历史重大黑天鹅事件的市场 OHLCV 行情并保存到本地以供离线测试。
    """
    output_dir = "src/backtest/extreme_data"
    os.makedirs(output_dir, exist_ok=True)
    
    # 我们关注单只科技巨头 AAPL，以及常作为避险属性消费组的替代品对比 KO (可口可乐) 和 PEP (百事可乐)
    tickers = ["AAPL", "KO", "PEP"]
    
    events = {
        "2008_Subprime_Crisis": {
            # 2008 雷曼兄弟破产（2008年9月15日）前后的主跌浪，往前多拉一年防指标计算缺数据
            "start": "2007-08-01",
            "end": "2008-12-31"
        },
        "2020_Covid_Crash": {
            # 2020 美股因疫情四次熔断（发生在3月份），同样提前一年拉取垫底数据
            "start": "2019-06-01",
            "end": "2020-05-15"
        }
    }
    
    print("🚀 开始为隔离测试舱抓取黑天鹅行情...")
    for event_name, dates in events.items():
        event_folder = os.path.join(output_dir, event_name)
        os.makedirs(event_folder, exist_ok=True)
        
        for ticker in tickers:
            print(f"📥 正在获取 {event_name} 期间 {ticker} 的数据...")
            try:
                data = yf.download(ticker, start=dates["start"], end=dates["end"], progress=False, multi_level_index=False)
                if not data.empty:
                    # Save OHLCV to CSV
                    csv_path = os.path.join(event_folder, f"{ticker}_price.csv")
                    data.to_csv(csv_path)
                    print(f"✅ 保存成功: {csv_path}")
                else:
                    print(f"⚠️ 未找到 {ticker} 在此期间的数据。")
            except Exception as e:
                print(f"❌ 抓取失败 {ticker}: {e}")
                
if __name__ == "__main__":
    fetch_extreme_event_data()
