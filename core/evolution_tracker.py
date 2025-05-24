import json
import os
import logging
from datetime import datetime
from typing import Any, Dict
from filelock import FileLock

class EvolutionTracker:
    """
    進化イベント・履歴（進化案の内容、適用日時、旧→新のdiff等）をlogs/evolution_log.jsonに記録する
    """
    def __init__(self, log_path="logs/evolution_log.json"):
        self.log_path = log_path
        self.lock_path = self.log_path + ".lock"
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)
        # 初期化（ファイルがなければ空リストで作成）
        if not os.path.exists(self.log_path):
            with open(self.log_path, "w", encoding="utf-8") as f:
                json.dump([], f, ensure_ascii=False, indent=2)

    def record(self, event: Dict[str, Any]):
        """
        進化イベントを追記記録する
        event例: {
            "timestamp": ..., "type": ..., "details": ..., "diff": ...
        }
        """
        event["timestamp"] = datetime.utcnow().isoformat()
        try:
            with FileLock(self.lock_path):
                with open(self.log_path, encoding="utf-8") as f:
                    logs = json.load(f)
                logs.append(event)
                with open(self.log_path, "w", encoding="utf-8") as f:
                    json.dump(logs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"EvolutionTracker record error: {e}, event={event}") 