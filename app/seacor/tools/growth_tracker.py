import os
import json
from datetime import datetime

# JSONL形式で成長イベントを記録
HISTORY_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'growth_history.jsonl'))

def record_event(event_type: str, details: dict):
    """成長イベントをファイルに追記"""
    entry = {'timestamp': datetime.utcnow().isoformat() + 'Z', 'event_type': event_type, 'details': details}
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, 'a', encoding='utf-8') as f:
        f.write(json.dumps(entry, ensure_ascii=False) + '\n')

def get_history() -> list:
    """履歴ファイルを読み込んでリストを返却"""
    if not os.path.exists(HISTORY_FILE):
        return []
    history = []
    with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                history.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return history
