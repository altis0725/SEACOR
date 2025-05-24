import yaml
import logging
from typing import List, Dict, Any
from core.yaml_validator import YAMLValidator

class AgentGenerator:
    """
    進化案（新Agent/Task/flow/manager_agent等）をYAMLに安全に追加・バリデーション・再ロードする
    """

    def __init__(self, agents_yaml_path, tasks_yaml_path, crews_yaml_path):
        self.agents_yaml_path = agents_yaml_path
        self.tasks_yaml_path = tasks_yaml_path
        self.crews_yaml_path = crews_yaml_path

    def _load_yaml(self, path, wrap_key=None):
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
            if wrap_key and wrap_key in data:
                return data[wrap_key]
            return data

    def _save_yaml(self, path, data, wrap_key=None):
        with open(path, "w", encoding="utf-8") as f:
            if wrap_key:
                yaml.safe_dump({wrap_key: data}, f, allow_unicode=True)
            else:
                yaml.safe_dump(data, f, allow_unicode=True)

    def add_agents(self, new_agents: List[Dict[str, Any]]):
        agents = self._load_yaml(self.agents_yaml_path, wrap_key="MetaAgent")
        validator = YAMLValidator(agents, self._load_yaml(self.tasks_yaml_path, wrap_key="MetaTask"))
        valid_agents = []
        for agent in new_agents:
            if validator.validate_agent(agent):
                valid_agents.append(agent)
            else:
                logging.warning(f"バリデーションNG: {agent.get('name', agent.get('id', 'unknown'))}（重複または必須項目不足）")
        if not valid_agents:
            logging.warning("有効な新規エージェントがありません。ロールバックします。")
            return
        for agent in valid_agents:
            agents[agent["id"]] = agent
        self._save_yaml(self.agents_yaml_path, agents, wrap_key="MetaAgent")

    def remove_agents(self, remove_agent_ids: List[str]):
        agents = self._load_yaml(self.agents_yaml_path, wrap_key="MetaAgent")
        for agent_id in remove_agent_ids:
            if agent_id in agents:
                del agents[agent_id]
                logging.info(f"エージェント削除: {agent_id}")
        self._save_yaml(self.agents_yaml_path, agents, wrap_key="MetaAgent")

    def merge_agents(self, merge_instructions: List[Dict[str, Any]]):
        agents = self._load_yaml(self.agents_yaml_path, wrap_key="MetaAgent")
        for merge in merge_instructions:
            from_ids = merge.get("from", [])
            to_id = merge.get("to")
            definition = merge.get("definition", {})
            # from_idsを削除し、to_idで新規追加
            for agent_id in from_ids:
                if agent_id in agents:
                    del agents[agent_id]
                    logging.info(f"エージェント統合: {agent_id} → {to_id}")
            if to_id and definition:
                agents[to_id] = definition
                logging.info(f"エージェント新規統合定義: {to_id}")
        self._save_yaml(self.agents_yaml_path, agents, wrap_key="MetaAgent")

    def add_tasks(self, new_tasks: List[Dict[str, Any]]):
        tasks = self._load_yaml(self.tasks_yaml_path, wrap_key="MetaTask")
        validator = YAMLValidator(self._load_yaml(self.agents_yaml_path, wrap_key="MetaAgent"), tasks)
        valid_tasks = []
        for task in new_tasks:
            if validator.validate_task(task):
                valid_tasks.append(task)
            else:
                logging.warning(f"バリデーションNG: {task.get('description', task.get('id', 'unknown'))}（重複または必須項目不足）")
        if not valid_tasks:
            logging.warning("有効な新規タスクがありません。ロールバックします。")
            return
        for task in valid_tasks:
            tasks[task["id"]] = task
        self._save_yaml(self.tasks_yaml_path, tasks, wrap_key="MetaTask")

    def update_crew(self, crew_name: str, updates: Dict[str, Any]):
        crews = self._load_yaml(self.crews_yaml_path, wrap_key="MetaCrew")
        if crew_name in crews:
            crews[crew_name].update(updates)
        else:
            crews[crew_name] = updates
        self._save_yaml(self.crews_yaml_path, crews, wrap_key="MetaCrew")

    def validate_yaml(self, path):
        # TODO: pydantic等でスキーマバリデーションを実装
        return True

    def apply_evolution(self, evolution: Dict[str, Any]):
        # 進化案に従い追加・削除・統合を適用
        if "new_agents" in evolution:
            self.add_agents(evolution["new_agents"])
        if "remove_agents" in evolution:
            self.remove_agents(evolution["remove_agents"])
        if "merge_agents" in evolution:
            self.merge_agents(evolution["merge_agents"])
        # タスクやクルーの進化も同様に拡張可

    def reload(self):
        # YAML再ロード用のフック（必要に応じて呼び出し）
        pass 