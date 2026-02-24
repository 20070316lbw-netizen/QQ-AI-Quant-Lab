import os

BACKTEST_CONFIG = {
    # 大型测试股票池：包含科技巨头、消费代表与金融板块
    "universe": [
        "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL",
        "META", "TSLA", "AVGO", "COST", "WMT",
        "JPM", "BAC", "V", "JNJ", "PG"
    ],
    
    # 将回测范围扩展至完整的 2 年期
    "start_date": "2024-02-01",
    "end_date": "2026-02-01",
    
    # 评测未来 N 天的统计特征
    "horizons": [1, 5],
    
    # 结果落地目录
    "output_dir": "src/backtest/results"
}
