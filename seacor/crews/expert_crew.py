import json
import re
import asyncio
from pathlib import Path
from typing import List, Dict, Any

from seacor.utils.logger import get_logger
from seacor.utils.config_loader import ConfigLoader
from seacor.tools.llm_providers import LLMConfig, LLMFactory
from seacor.agents.agent_factory import create_expert_agent
from seacor.utils.config_models import ExpertConfig
from crewai import Task

logger = get_logger(__name__)

class ExpertCrew:
    """
    LLMベースのオーケストレーションを行うSEACORの中核クラス。
    自己進化型プロンプトを Manager LLM に投げ、結果を解析・実行・評価・強化・記録まで行う。
    """

    def __init__(self, llm_config: LLMConfig, config_dir: str = "config"):
        self.loader = ConfigLoader(config_dir)
        self.llm = LLMFactory.get_llm(llm_config)
        # 専門家エージェントを全て生成
        self.experts: List = [
            create_expert_agent(cfg, llm_config, self.loader.create_tools(llm_config))
            for cfg in self.loader.get_expert_configs()
        ]
        self.log_path = Path("evolution_log.jsonl")

    async def process_query(self, prompt: str) -> str:
        logger.info(f"Query received: {prompt}")
        expertise = await self._analyze(prompt)
        plan = await self._plan(prompt, expertise)
        results = await self._execute(plan, prompt)
        evaluation = await self._self_evaluate(plan, results)
        improvements = await self._reinforce(evaluation)
        await self._record(prompt, plan, results, evaluation, improvements)
        await self._evolve_proposal(prompt, results, evaluation, improvements)
        # ユーザーには実行結果のみ返す
        return "\n\n".join(results)

    async def _analyze(self, prompt: str) -> List[str]:
        """
        STEP 1: 必要な専門分野を分析し JSON 配列で返す
        """
        msg = (
            "STEP 1: 以下のクエリに対して必要な専門分野をJSON配列で出力してください:\n"
            f"{prompt}"
        )
        resp = await self.llm.agenerate([msg])
        text = resp.generations[0][0].text
        m = re.search(r"\[.*?\]", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except:
                pass
        # フォールバック：すべてのエキスパートの専門分野を返す
        return list({e for cfg in self.loader.get_expert_configs() for e in cfg.expertise})

    async def _plan(self, prompt: str, expertise: List[str]) -> Dict[str, Any]:
        """
        STEP 2: 実行計画をJSONで生成（タスクID, description, dependencies）
        """
        msg = (
            "STEP 2: 以下のクエリと利用可能な専門分野に基づき、"
            "実行計画をJSON形式で出力してください。フォーマットは:\n"
            '{"tasks":[{"id":"t1","description":"...","expertise":["..."]}],'
            '"dependencies":{"t2":["t1"]}}}\n'
            f"Query: {prompt}\n"
            f"Expertise: {expertise}"
        )
        resp = await self.llm.agenerate([msg])
        text = resp.generations[0][0].text
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group())
            except:
                pass
        # フォールバック：シンプル1タスク
        return {"tasks":[{"id":"t1","description":prompt,"expertise":expertise}], "dependencies":{}}

    async def _execute(self, plan: Dict[str, Any], prompt: str) -> List[str]:
        """
        STEP 3: トポロジカルソートで依存順を保証し、各タスクを実行
        """
        deps = plan.get("dependencies", {})
        graph = {t["id"]: set(deps.get(t["id"], [])) for t in plan["tasks"]}
        ordered = []
        while graph:
            ready = [nid for nid, ins in graph.items() if not ins]
            if not ready:
                break
            for nid in ready:
                ordered.append(nid)
                del graph[nid]
                for ins in graph.values():
                    ins.discard(nid)
        desc_map = {t["id"]: t["description"] for t in plan["tasks"]}
        results = []
        for tid in ordered:
            desc = desc_map[tid]
            # 簡易スコアリングで最適エキスパートを選定
            expert = max(
                self.experts,
                key=lambda e: sum(cap in desc for cap in e.config.expertise)
            )
            logger.info(f"Executing {tid} ({desc}) with {expert.config.name}")
            task = Task(description=desc, expected_output="テキストによる回答")
            res = expert.execute_task(task, {"prompt": prompt})
            results.append(res)
        return results

    async def _self_evaluate(self, plan: Dict[str, Any], results: List[str]) -> str:
        """
        STEP 4: 実行結果を自己評価し、弱点やギャップをテキストで返す
        """
        msg = (
            "STEP 4: 以下の実行結果について、弱点やギャップを指摘してください:\n"
            f"Plan: {plan}\nResults: {results}"
        )
        resp = await self.llm.agenerate([msg])
        return resp.generations[0][0].text

    async def _reinforce(self, evaluation: str) -> str:
        """
        STEP 5: 評価に基づき、改善策をテキストで返す
        """
        msg = (
            "STEP 5: 以下の評価を元に、改善策や次のステップを具体的に提案してください:\n"
            f"Evaluation: {evaluation}"
        )
        resp = await self.llm.agenerate([msg])
        return resp.generations[0][0].text

    async def _record(
        self,
        prompt: str,
        plan: Dict[str, Any],
        results: List[str],
        evaluation: str,
        improvements: str
    ):
        """
        STEP 6: 自己進化の履歴を JSONL に記録
        """
        entry = {
            "prompt": prompt,
            "plan": plan,
            "results": results,
            "evaluation": evaluation,
            "improvements": improvements,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat()
        }
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    async def _evolve_proposal(self, prompt, results, evaluation, improvements):
        """
        プロンプト・回答・評価・改善提案をもとに、足りない/修正が必要な専門家のYAML提案をLLMに生成させ、ログ出力する（自動反映はしない）。
        """
        msg = (
            "以下のプロンプト・AIの回答・評価・改善提案を比較し、"
            "足りない専門分野や追加・修正が必要な専門家があれば、YAML形式で提案してください。"
            "既存のexperts.yamlの一部だけを出力してください。なければ'No change'とだけ返してください。\n"
            f"プロンプト: {prompt}\n"
            f"回答: {results}\n"
            f"評価: {evaluation}\n"
            f"改善提案: {improvements}\n"
            "出力例:\nexperts:\n  - name: ...\n    expertise: [...]\n"
        )
        resp = await self.llm.agenerate([msg])
        proposal = resp.generations[0][0].text.strip()
        logger.info(f"[自己進化提案]\n{proposal}")