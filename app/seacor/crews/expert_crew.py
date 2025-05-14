from typing import List, Dict, Any, Optional, Set
from crewai import Crew, Task, Process
from pydantic import BaseModel, Field
from app.seacor.tools.llm_providers import LLMConfig, LLMFactory
from app.seacor.tools.base_tool import Tool, WebSearchTool, CodeAnalysisTool
from app.seacor.agents.expert_agent import ExpertAgent, ExpertConfig as AgentExpertConfig
from app.seacor.utils.logger import get_logger
from app.seacor.utils.config_loader import ConfigLoader
import asyncio
import logging
import sys
import json

# モジュールレベルのロガー
logger = get_logger(__name__)

class ExecutionPlan(BaseModel):
    """実行計画"""
    tasks: List[Task]
    parallel_tasks: List[List[Task]]
    dependencies: Dict[str, List[str]]
    original_query: str

class ExpertCrew:
    """専門家を束ねる処理"""
    def __init__(
        self,
        llm_config: LLMConfig,
        config_dir: str = "app/config"
    ):
        """ExpertCrewの初期化
        
        Args:
            llm_config: LLMの設定
            config_dir: 設定ファイルのディレクトリパス。デフォルトは'app/config'
        """
        self.llm_config = llm_config
        self._config_loader = ConfigLoader(config_dir)
        self.tools = list(self._config_loader.create_tools(llm_config).values())
        self.experts: Dict[str, ExpertAgent] = {}  # 名前 -> エージェント
        self._expertise_registry: Dict[str, List[ExpertAgent]] = {}  # 専門分野 -> エージェントリスト
        self._llm = LLMFactory.get_llm(llm_config)
        self.logger = logger  # モジュールレベルのロガーを使用
        self._initialize_experts()

    def _initialize_experts(self):
        """初期の専門家を設定"""
        self.logger.info("専門家の初期化を開始")
        
        # 設定から専門家を作成
        for expert_config in self._config_loader.get_expert_configs():
            # ツールの選択
            expert_tools = [
                tool for tool in self.tools
                if tool.config.name in expert_config.tools
            ]
            
            # 専門家の作成
            expert = ExpertAgent(
                config=AgentExpertConfig(
                    name=expert_config.name,
                    expertise=expert_config.expertise,
                    tools=expert_tools,
                    llm_config=self.llm_config,
                    goal=expert_config.goal,
                    backstory=expert_config.backstory
                )
            )
            
            # 専門家の登録
            self.register_expert(expert)
        
        self.logger.info(f"初期化された専門家: {list(self.experts.keys())}")
        self.logger.info(f"登録された専門分野: {list(self._expertise_registry.keys())}")

    def register_expert(self, expert: ExpertAgent) -> None:
        """エージェントを登録"""
        self.logger.info(f"専門家 '{expert.name}' の登録を開始")
        
        # 名前による登録
        self.experts[expert.name] = expert
        
        # 専門分野による登録
        for expertise in expert.get_capabilities():
            if expertise not in self._expertise_registry:
                self._expertise_registry[expertise] = []
            if expert not in self._expertise_registry[expertise]:
                self._expertise_registry[expertise].append(expert)
        
        self.logger.info(f"専門家 '{expert.name}' の登録が完了")
        self.logger.info(f"登録された専門分野: {list(expert.get_capabilities())}")

    def get_experts_by_expertise(self, expertise: str) -> List[ExpertAgent]:
        """専門分野に基づいて専門家を取得"""
        return self._expertise_registry.get(expertise, [])

    def get_all_experts(self) -> List[ExpertAgent]:
        """登録されている全ての専門家を取得"""
        return list(self.experts.values())

    def get_all_expertise(self) -> Set[str]:
        """利用可能な全ての専門分野を取得"""
        return set(self._expertise_registry.keys())

    async def process_query(self, query: str) -> str:
        """クエリの処理"""
        self.logger.info(f"元のクエリ: {query}")
        
        # 必要な専門分野の分析
        required_expertise = await self._analyze_required_expertise(query)
        self.logger.info(f"必要な専門分野: {required_expertise}")
        
        # 必要な専門家の確保
        await self._ensure_experts(required_expertise)
        
        # 利用可能な専門家の確認
        available_experts = self.get_all_experts()
        self.logger.info(f"利用可能な専門家: {[expert.name for expert in available_experts]}")
        self.logger.info(f"利用可能な専門分野: {self.get_all_expertise()}")
        
        # 実行計画の生成
        plan = await self._create_execution_plan(query, required_expertise)
        if not plan:
            return "申し訳ありませんが、クエリの処理計画を生成できませんでした。"

        # 実行結果を格納する辞書
        results = {}
        
        # タスクの実行
        for task in plan.tasks:
            task_desc = task.description
            self.logger.info(f"タスク実行: {task_desc}")
            
            # タスクを実行できるエキスパートを探す
            expert = self._find_expert_for_task(task)
            if not expert:
                self.logger.warning(f"タスク '{task_desc}' を実行できる専門家が見つかりません")
                continue
                
            result = await expert.execute_task(task_desc, {"original_query": query})
            if result:
                results[task_desc] = result

        # 並列タスクの実行
        for parallel_group in plan.parallel_tasks:
            self.logger.info(f"並列タスクグループの実行: {[t.description for t in parallel_group]}")
            group_results = []
            
            for task in parallel_group:
                task_desc = task.description
                expert = self._find_expert_for_task(task)
                if expert:
                    result = await expert.execute_task(task_desc, {"original_query": query})
                    if result:
                        group_results.append(result)
            
            if group_results:
                # 並列タスクの結果を統合
                results[f"parallel_{len(results)}"] = "\n".join(group_results)

        # 結果の統合と重複の排除
        final_result = self._merge_results(results)
        return final_result

    def _merge_results(self, results: Dict[str, str]) -> str:
        """実行結果を統合し、重複を排除"""
        if not results:
            return "申し訳ありませんが、クエリに対する適切な回答を生成できませんでした。"

        # 結果を結合
        combined = "\n\n".join(results.values())
        
        # 重複するセクションを特定して削除
        sections = combined.split("\n\n")
        unique_sections = []
        seen = set()
        
        for section in sections:
            # セクションの主要な内容を抽出（最初の数行）
            key = "\n".join(section.split("\n")[:3])
            if key not in seen:
                seen.add(key)
                unique_sections.append(section)
        
        return "\n\n".join(unique_sections)

    def _find_expert_for_task(self, task: Task) -> Optional[ExpertAgent]:
        """タスクに最適なエキスパートを探す"""
        task_desc = task.description.lower()
        best_expert = None
        max_match = 0
        
        # タスクの説明から必要な専門分野を推測
        for expert in self.experts.values():
            match_count = sum(
                1 for capability in expert.get_capabilities()
                if capability.lower() in task_desc
            )
            if match_count > max_match:
                max_match = match_count
                best_expert = expert
        
        if best_expert:
            self.logger.info(f"タスク '{task.description}' に最適な専門家: {best_expert.name}")
            self.logger.info(f"マッチした専門分野: {[cap for cap in best_expert.get_capabilities() if cap.lower() in task_desc]}")
        
        return best_expert

    async def _analyze_required_expertise(self, query: str) -> List[str]:
        """クエリに必要な専門分野の分析"""
        prompt = f"""
        以下のクエリを処理するために必要な専門分野を特定してください：
        {query}
        
        専門分野は具体的で、実行可能なものにしてください。
        以下の形式でJSON配列として出力してください：
        [
            "専門分野1",
            "専門分野2",
            ...
        ]
        
        注意点：
        - 専門分野は具体的で、実行可能なものにしてください
        - 例：論理分析、コード最適化、セキュリティ評価、データ分析など
        - 最低1つ、最大5つまでの専門分野を提案してください
        """
        
        response = await self._llm.agenerate([prompt])
        try:
            # LLMの応答からJSONを抽出
            import json
            import re
            
            # 応答からJSON配列部分を抽出
            json_match = re.search(r'\[.*\]', response.generations[0][0].text, re.DOTALL)
            if not json_match:
                raise ValueError("JSON array not found in response")
            
            expertise_list = json.loads(json_match.group())
            
            # 専門分野の検証
            if not isinstance(expertise_list, list):
                raise ValueError("Response is not a list")
            if not expertise_list:
                raise ValueError("Empty expertise list")
            if len(expertise_list) > 5:
                expertise_list = expertise_list[:5]
            
            return expertise_list
            
        except Exception as e:
            # エラー時はデフォルトの専門分野を返す
            return ["論理分析", "コード最適化"]

    async def _ensure_experts(self, required_expertise: List[str]):
        """必要な専門家を確保"""
        self.logger.info("必要な専門家の確保を開始")
        self.logger.info(f"必要な専門分野: {required_expertise}")
        
        for expertise in required_expertise:
            # 既存の専門家を確認
            existing_experts = self.get_experts_by_expertise(expertise)
            if not existing_experts:
                self.logger.info(f"専門分野 '{expertise}' の専門家が存在しないため、新規作成します")
                try:
                    # 新しい専門家の設定を生成
                    expert_config = await self._generate_expert_config([expertise])
                    self.logger.info(f"専門家の設定を生成: {json.dumps(expert_config, ensure_ascii=False, indent=2)}")
                    
                    # 新しい専門家を作成
                    expert = ExpertAgent(
                        config=AgentExpertConfig(
                            name=expert_config["name"],
                            expertise=expert_config["expertise"],
                            tools=self.tools,  # 既存のツールを使用
                            llm_config=self.llm_config,
                            goal=expert_config["goal"],
                            backstory=expert_config["backstory"]
                        )
                    )
                    
                    # 専門家を登録
                    self.register_expert(expert)
                    self.logger.info(f"専門家 '{expert.name}' の作成と登録が完了")
                except Exception as e:
                    self.logger.error(f"専門家の作成中にエラーが発生: {str(e)}")
                    raise
            else:
                self.logger.info(f"専門分野 '{expertise}' の専門家が既に存在します: {[exp.name for exp in existing_experts]}")
        
        self.logger.info("必要な専門家の確保が完了")

    async def _generate_expert_config(self, expertise: List[str]) -> Dict[str, Any]:
        """専門家の設定を生成"""
        self.logger.info("専門家の設定生成を開始")
        self.logger.info(f"専門分野: {expertise}")
        
        prompt = f"""
        以下の専門分野を持つ専門家の設定を生成してください：
        {', '.join(expertise)}
        
        以下の形式でJSONオブジェクトとして出力してください：
        {{
            "name": "専門家の名前",
            "expertise": ["専門分野1", "専門分野2", ...],
            "goal": "専門家の目標",
            "backstory": "専門家の背景ストーリー"
        }}
        
        注意点：
        - 名前は具体的で、専門分野を反映したものにしてください
        - 目標は具体的で、実行可能なものにしてください
        - 背景ストーリーは専門家の経験と能力を説明するものにしてください
        - 専門分野は必ず入力された専門分野を含めてください
        - 必要に応じて関連する専門分野を追加しても構いません
        """
        
        response = await self._llm.agenerate([prompt])
        try:
            # LLMの応答からJSONを抽出
            import re
            
            # 応答からJSONオブジェクト部分を抽出
            json_match = re.search(r'\{.*\}', response.generations[0][0].text, re.DOTALL)
            if not json_match:
                raise ValueError("JSON object not found in response")
            
            expert_config = json.loads(json_match.group())
            
            # 設定の検証
            required_fields = ["name", "expertise", "goal", "backstory"]
            for field in required_fields:
                if field not in expert_config:
                    raise ValueError(f"Missing required field: {field}")
            
            # 専門分野の検証と調整
            if not isinstance(expert_config["expertise"], list):
                raise ValueError("expertise must be a list")
            
            # 生成された専門分野に要求された専門分野が含まれているか確認
            generated_expertise = set(exp.lower() for exp in expert_config["expertise"])
            required_expertise = set(exp.lower() for exp in expertise)
            
            # 要求された専門分野が含まれていない場合、追加
            missing_expertise = required_expertise - generated_expertise
            if missing_expertise:
                self.logger.info(f"生成された専門分野に不足があるため、追加します: {missing_expertise}")
                expert_config["expertise"].extend(list(missing_expertise))
            
            # 重複を除去
            expert_config["expertise"] = list(dict.fromkeys(expert_config["expertise"]))
            
            self.logger.info("専門家の設定生成が完了")
            self.logger.info(f"最終的な専門分野: {expert_config['expertise']}")
            return expert_config
            
        except Exception as e:
            self.logger.error(f"専門家の設定生成中にエラーが発生: {str(e)}")
            raise

    async def _create_execution_plan(
        self,
        query: str,
        expertise: List[str]
    ) -> Optional[ExecutionPlan]:
        """実行計画の立案"""
        try:
            prompt = f"""
            以下のクエリを処理するための実行計画を立案してください：
            {query}
            
            利用可能な専門分野：
            {', '.join(expertise)}
            
            以下の形式でJSONとして出力してください：
            {{
                "tasks": [
                    {{
                        "description": "タスクの説明",
                        "expertise": ["必要な専門分野1", "必要な専門分野2"]
                    }}
                ],
                "parallel_tasks": [
                    [
                        {{
                            "description": "並列実行可能なタスク1",
                            "expertise": ["必要な専門分野"]
                        }},
                        {{
                            "description": "並列実行可能なタスク2",
                            "expertise": ["必要な専門分野"]
                        }}
                    ]
                ],
                "dependencies": {{
                    "タスクID": ["依存するタスクID1", "依存するタスクID2"]
                }}
            }}
            
            注意点：
            - タスクは具体的で実行可能な単位に分割してください
            - 並列実行可能なタスクは適切にグループ化してください
            - 依存関係は明確に定義してください
            """
            
            response = await self._llm.agenerate([prompt])
            
            # LLMの応答からJSONを抽出
            import json
            import re
            
            # 応答からJSON部分を抽出
            json_match = re.search(r'\{.*\}', response.generations[0][0].text, re.DOTALL)
            if not json_match:
                raise ValueError("JSON not found in response")
            
            plan_data = json.loads(json_match.group())
            
            # タスクの生成
            tasks = [
                Task(description=task["description"], expected_output="text")
                for task in plan_data.get("tasks", [])
            ]
            
            # 並列タスクの生成
            parallel_tasks = [
                [Task(description=task["description"], expected_output="text") for task in group]
                for group in plan_data.get("parallel_tasks", [])
            ]
            
            # 依存関係の設定
            dependencies = plan_data.get("dependencies", {})
            
            return ExecutionPlan(
                tasks=tasks,
                parallel_tasks=parallel_tasks,
                dependencies=dependencies,
                original_query=query
            )
            
        except Exception as e:
            self.logger.error(f"実行計画の生成中にエラーが発生: {str(e)}")
            # エラー時はシンプルな実行計画を返す
            return ExecutionPlan(
                tasks=[Task(description=query, expected_output="text")],
                parallel_tasks=[],
                dependencies={},
                original_query=query
            )

    def _select_best_expert(self, task_description: str) -> Optional[ExpertAgent]:
        """タスクに最適な専門家を選択"""
        best_expert = None
        max_match = 0
        
        for expert in self.experts.values():
            match_count = sum(
                1 for capability in expert.get_capabilities()
                if capability.lower() in task_description.lower()
            )
            if match_count > max_match:
                max_match = match_count
                best_expert = expert
        
        return best_expert 