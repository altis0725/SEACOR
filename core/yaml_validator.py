import yaml
from typing import List, Dict, Any
import logging
from core.evolution_tracker import EvolutionTracker
from crews.generic_crew import kickoff_async_crew

class YAMLValidator:
    def __init__(self, agents: Dict[str, Any], tasks: Dict[str, Any]):
        self.agents = agents
        self.tasks = tasks
        self.evolution_tracker = EvolutionTracker()

    def is_duplicate_agent(self, new_agent: Dict[str, Any]) -> bool:
        for agent_id, agent in self.agents.items():
            if agent_id == new_agent.get("id"):
                return True
            if (agent.get("name") == new_agent.get("name") and
                agent.get("role") == new_agent.get("role") and
                agent.get("goal") == new_agent.get("goal") and
                agent.get("tools") == new_agent.get("tools")):
                return True
        return False

    def is_duplicate_task(self, new_task: Dict[str, Any]) -> bool:
        for task_id, task in self.tasks.items():
            if task_id == new_task.get("id"):
                return True
            if (task.get("description") == new_task.get("description") and
                task.get("expected_output") == new_task.get("expected_output")):
                return True
        return False

    async def ai_validate_agent(self, new_agent: Dict[str, Any]) -> bool:
        # 既存エージェント一覧をsystem_messageとして渡す
        system_message = str(list(self.agents.values()))
        result = await kickoff_async_crew(
            "validation_crew",
            prompt=str(new_agent),
            system_message=system_message
        )
        # ログ・進化履歴に記録
        logging.info(f"AIバリデーション結果: {result}")
        self.evolution_tracker.record({
            "type": "ai_validation",
            "target": "agent",
            "input": new_agent,
            "result": str(result)
        })
        # AIの返答がdict形式で返る前提
        if hasattr(result, "raw"):
            import json
            try:
                ai_result = json.loads(result.raw)
                return not ai_result.get("is_duplicate", False)
            except Exception as e:
                logging.error(f"AIバリデーションのパース失敗: {e}, result={result}")
                return True  # パース失敗時は重複扱い
        return True

    async def validate_agent(self, agent: Dict[str, Any]) -> bool:
        # 単一YAMLのdict構造に合わせて必須キーを確認
        required = ["id", "name", "role", "goal", "tools"]
        rule_valid = all(k in agent for k in required) and not self.is_duplicate_agent(agent)
        if not rule_valid:
            return False
        # AIバリデーションも併用
        return await self.ai_validate_agent(agent)

    def validate_task(self, task: Dict[str, Any]) -> bool:
        required = ["id", "description", "agent"]
        return all(k in task for k in required) and not self.is_duplicate_task(task) 