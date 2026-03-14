import json
import os
import datetime

class ExperimentTracker:
    def __init__(self, log_path=None, sync_path=None):
        if log_path is None:
            # Default to tracking in configs dir
            self.log_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "configs", "experiments_log.json")
        else:
            self.log_path = log_path
            
        self.sync_path = sync_path # Git Repo path for project-specific logs
        
        # Ensure directories exist
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        if self.sync_path:
            os.makedirs(os.path.dirname(self.sync_path), exist_ok=True)
        
        # Initialize file if not exists
        if not os.path.exists(self.log_path):
            with open(self.log_path, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=4)

    def log_experiment(self, dataset_name, horizon, features, results, 
                       questions="无记录", methodology="无记录", notes=""):
        """
        Record a new experiment into the JSON log.
        """
        # 增加防御：递归清洗 results 中的 NaN / Inf，防止污染 JSON
        def clean_data(val):
            if isinstance(val, (float, int)):
                if val != val or val == float('inf') or val == float('-inf'):
                    return None # JSON 不支持 NaN，转换为 null
            elif isinstance(val, dict):
                return {k: clean_data(v) for k, v in val.items()}
            elif isinstance(val, list):
                return [clean_data(i) for i in val]
            return val

        entry = {
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "dataset": dataset_name,
            "horizon": horizon,
            "features": features,
            "questions": questions,     # 质疑与提问 (研究动机)
            "methodology": methodology, # 测试方法与逻辑
            "results": clean_data(results),
            "notes": notes
        }
        
        try:
            with open(self.log_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = []
            
        data.append(entry)
        
        # Save to both locations
        for path in [self.log_path, self.sync_path]:
            if path:
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
        
        print(f"✅ 实验记录已写入 -> {self.log_path}")
        if self.sync_path:
            print(f"🔄 已同步镜像至 -> {self.sync_path}")
        return entry
