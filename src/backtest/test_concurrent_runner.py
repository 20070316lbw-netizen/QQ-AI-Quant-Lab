import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# 动态重写全局配置用于疾速并发验证
import backtest.config as config_module
config_module.BACKTEST_CONFIG["universe"] = ["AAPL", "MSFT", "TSLA"]
config_module.BACKTEST_CONFIG["start_date"] = "2025-11-01"
config_module.BACKTEST_CONFIG["end_date"] = "2025-12-31"

import multiprocessing
from backtest.backtest_runner import run_backtest

if __name__ == '__main__':
    multiprocessing.freeze_support()
    print("====== 🚀 启动验证并发引擎边界测试 (AAPL/MSFT/TSLA, 2025十一月至十二月) ======")
    run_backtest()
