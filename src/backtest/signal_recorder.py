import os
import json
from datetime import datetime

class SignalRecorder:
    """
    负责以细粒度落盘 Z-Score 回测日志，供 Performance Analyzer 使用
    """
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir, exist_ok=True)
            
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.record_file = os.path.join(self.output_dir, f"backtest_records_{timestamp}.jsonl")
        
    def save_batch(self, records: list):
        if not records:
            return
            
        with open(self.record_file, "a", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        print(f"[Recorder] Saved {len(records)} records to {self.record_file}")
        
    def load_latest_records(self) -> list:
        # 获取最新的日志文件
        files = [f for f in os.listdir(self.output_dir) if f.startswith("backtest_records_")]
        if not files:
            return []
        
        latest_file = max(files)
        file_path = os.path.join(self.output_dir, latest_file)
        
        records = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
        return records
        
    def get_latest_file_path(self) -> str:
        files = [f for f in os.listdir(self.output_dir) if f.startswith("backtest_records_")]
        if not files:
            return ""
        return os.path.join(self.output_dir, max(files))
