import os

BACKTEST_CONFIG = {
    # 大型测试股票池：包含科技巨头、消费代表与金融板块
    "universe": [
        "AAPL", "MSFT", "NVDA", "AMZN", "GOOGL",
        "META", "TSLA", "AVGO", "COST", "WMT",
        "JPM", "BAC", "V", "JNJ", "PG"
    ],
    
    # 世纪大回测专属：涵盖 2023, 2024, 2025 的全交易日
    "start_date": "2023-01-01",
    "end_date": "2025-12-31",
    
    # 评测未来 N 天的统计特征
    "horizons": [1, 5],
    
    # 结果落地目录
    "output_dir": "src/backtest/results"
}
