import os
import yaml
import json
from utils.backup_and_rollback import backup_configs
import logging

AGENTS_PATH = "config/agents/main_agents.yaml"
CREWS_DIR = "config/crews"

REQUIRED_AGENT_FIELDS = ["name", "goal", "role", "backstory"]

logging.basicConfig(filename='logs/task.log', level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')

def load_yaml(path):
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)

def save_yaml(path, data):
    with open(path, "w", encoding="utf-8") as f:
        yaml.safe_dump(data, f, allow_unicode=True)

def apply_evolution(evo: dict):
    # 1. バックアップ
    backup_configs()
    # 2. agentsロード
    agents = load_yaml(AGENTS_PATH)
    # 3. 新規agent追加
    new_agents = evo.get("new_agents", [])
    for agent in new_agents:
        if isinstance(agent, dict):
            # 不足属性を自動補完
            for field in REQUIRED_AGENT_FIELDS:
                if field not in agent:
                    agent[field] = ""
            key = agent.get("id") or agent.get("name")
            if key:
                agents[key] = agent
            else:
                logging.warning(f"[警告] agent定義にid/nameがありません: {agent}")
        elif isinstance(agent, str):
            logging.warning(f"[警告] agent定義が不完全: {agent}")
    # 4. agent削除
    remove_agents = evo.get("remove_agents", [])
    for agent in remove_agents:
        if isinstance(agent, dict):
            key = agent.get("id") or agent.get("name")
            if key and key in agents:
                del agents[key]
        elif isinstance(agent, str):
            if agent in agents:
                del agents[agent]
    # 5. agent統合（merge_agents）
    for merge in evo.get("merge_agents", []):
        if "from" in merge and "to" in merge and "definition" in merge:
            for aid in merge["from"]:
                if aid in agents:
                    del agents[aid]
            agents[merge["to"]] = merge["definition"]
    # 6. agents保存
    save_yaml(AGENTS_PATH, agents)

    # === crews/flowの自動適用 ===
    # 追加・削除は無効化
    # 修正のみ: update_crews
    update_crews = evo.get("update_crews", [])
    for crew in update_crews:
        if isinstance(crew, dict):
            crew_name = crew.get("name")
            if not crew_name:
                logging.warning(f"[警告] crew修正定義にnameがありません: {crew}")
                continue
            path = os.path.join(CREWS_DIR, f"{crew_name}.yaml")
            if os.path.exists(path):
                save_yaml(path, {"MetaCrew": crew})
                logging.info(f"クルー修正: {crew_name}")
            else:
                logging.warning(f"[警告] crewファイルが存在しません（修正スキップ）: {path}")
        else:
            logging.warning(f"[警告] crew修正定義が不完全: {crew}")
    logging.info(f"進化案を適用しました（YAML自動編集・クルー/フロー修正のみ）") 