import json
import logging
from tools.monica_llm import MonicaLLM

class SelfAssessor:
    """
    クルー実行結果をLLMで自己評価し、進化案（新Agent/Task/flow/manager_agent等）をJSONで返す
    """
    def __init__(self, llm: MonicaLLM):
        self.llm = llm

    def assess(self, result: str, prompt: str) -> dict:
        system_message = (
            "あなたはAIシステムの自己評価・進化提案の専門家です。"
            "以下の実行結果とプロンプトを分析し、"
            "不足しているスキル・新たに必要なエージェントやタスクの追加、"
            "類似エージェントの統合や不要エージェントの削除、"
            "改善点をJSONで提案してください。"
            "出力例: {\"new_agents\": [...], \"remove_agents\": [...], \"merge_agents\": [...], \"improvements\": [...], \"flow\": \"parallel\", \"manager_agent\": \"main_agent_1\"}"
        )
        user_message = f"プロンプト:\n{prompt}\n\n実行結果:\n{result}"
        response = self.llm.chat([
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ])
        try:
            return json.loads(response["choices"][0]["message"]["content"])
        except Exception as e:
            logging.error(f"SelfAssessor JSON decode error: {e}, response={response}")
            return {"error": str(e), "raw": response} 