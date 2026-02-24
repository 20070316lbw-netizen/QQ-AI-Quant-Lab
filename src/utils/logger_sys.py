import os
import json
import uuid
import threading
from datetime import datetime

# 全局写锁防止多线程/多进程写入打架
_log_lock = threading.Lock()

class TradingLogger:
    """
    负责在每个交易周期结束后记录不可篡改的决策快照 (Snapshot)
    """
    def __init__(self, log_dir="logs"):
        self.log_dir = log_dir
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir, exist_ok=True)
            
        # 每天创建一个独立的回测文件
        today = datetime.now().strftime("%Y-%m-%d")
        self.log_file = os.path.join(self.log_dir, f"decisions_{today}.jsonl")

    def log_decision(self, signal_pack: dict):
        """
        接收来自 trading_signal 的信号包并将其序列化到文件
        """
        snapshot = {
            "snapshot_id": str(uuid.uuid4()),
            "timestamp": datetime.now().isoformat() + "Z",
        }
        # 将原始数据合并进来
        snapshot.update(signal_pack)
        
        with _log_lock:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(snapshot, ensure_ascii=False) + "\n")
                
# 全局唯一的日志实例
global_logger = TradingLogger()
