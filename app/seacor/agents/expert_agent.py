from typing import List, Dict, Any, Optional, Set
from crewai import Agent
from pydantic import BaseModel, Field, ConfigDict
from app.seacor.tools.llm_providers import LLMConfig, LLMFactory
from app.seacor.tools.base_tool import Tool
from app.seacor.utils.logger import get_logger
import logging
import re
import json

# モジュールレベルのロガー
logger = get_logger(__name__)

class ExpertConfig(BaseModel):
    """専門家の設定"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str
    expertise: List[str]
    tools: List[Tool]
    llm_config: LLMConfig
    goal: str
    backstory: Optional[str] = None
    verbose: bool = False

class ExpertAgent:
    """専門家エージェント"""
    def __init__(
        self,
        config: ExpertConfig,
        **kwargs
    ):
        # ロガーの初期化
        self._logger = get_logger(f"{__name__}.{config.name}")
        self._logger.info("="*50)
        self._logger.info("エージェントの初期化を開始")
        self._logger.info(f"設定: {json.dumps(config.model_dump(exclude={'tools', 'llm_config'}), ensure_ascii=False, indent=2)}")
        
        # LLMの初期化
        llm = LLMFactory.get_llm(config.llm_config)
        self._logger.info(f"LLMを初期化: {config.llm_config.model}")
        
        # Agentの初期化
        self._agent = Agent(
            name=getattr(config, "name", None) or getattr(config, "role", None) or "Expert",
            role=f"Expert in {', '.join(config.expertise)}",
            goal=config.goal,
            backstory=config.backstory or config.goal,
            llm=llm,
            verbose=config.verbose,
            allow_delegation=True,
            **kwargs
        )
        
        self.config = config
        self._capabilities: Set[str] = set(config.expertise)
        self._tools: Dict[str, Tool] = {
            tool.config.name: tool for tool in config.tools
        }
        self._logger.info(f"エージェント '{self._agent.role}' を初期化完了")
        self._logger.info(f"専門分野: {', '.join(self._capabilities)}")
        self._logger.info(f"利用可能なツール: {[tool.config.name for tool in self._tools.values()]}")
        self._logger.info("="*50)

    @property
    def logger(self) -> logging.Logger:
        """ロガーを取得"""
        return self._logger

    @property
    def role(self) -> str:
        """エージェントの役割を取得"""
        return self._agent.role

    @property
    def name(self) -> str:
        """エージェントの名前を取得"""
        return self.config.name

    def can_handle(self, task_description: str) -> bool:
        """タスクを処理できるか判断"""
        self.logger.info("-"*30)
        self.logger.info("タスク処理可否の判断を開始")
        self.logger.info(f"タスク内容: {task_description}")
        
        matching_capabilities = [
            capability for capability in self._capabilities
            if capability.lower() in task_description.lower()
        ]
        
        can_handle = bool(matching_capabilities)
        self.logger.info(f"マッチした専門分野: {matching_capabilities if matching_capabilities else 'なし'}")
        self.logger.info(f"処理可否: {can_handle}")
        self.logger.info("-"*30)
        return can_handle

    def evolve(self, new_capability: str, new_tool: Optional[Tool] = None):
        """新しい能力とツールを獲得"""
        self.logger.info("-"*30)
        self.logger.info("エージェントの進化を開始")
        self.logger.info(f"獲得する能力: {new_capability}")
        
        self._capabilities.add(new_capability)
        if new_tool:
            self._tools[new_tool.config.name] = new_tool
            self.logger.info(f"新しいツールを追加: {new_tool.config.name}")
        
        self.logger.info(f"現在の専門分野: {', '.join(self._capabilities)}")
        self.logger.info(f"現在のツール: {[tool.config.name for tool in self._tools.values()]}")
        self.logger.info("-"*30)

    async def execute_task(self, task_description: str, params: Dict = None) -> Optional[str]:
        """タスクの実行"""
        self.logger.info("="*50)
        self.logger.info("タスク実行を開始")
        self.logger.info(f"タスク内容: {task_description}")
        if params:
            self.logger.info(f"追加パラメータ: {params}")
        original_query = params.get("original_query", "") if params else ""
        self.logger.info(f"元のクエリ: {original_query}")

        # タスクの処理可否を判断
        self.logger.info("-"*50)
        self.logger.info("タスク処理可否の判断を開始")
        self.logger.info(f"タスク内容: {task_description}")
        
        matched_expertise = [
            exp for exp in self._capabilities
            if exp.lower() in task_description.lower()
        ]
        self.logger.info(f"マッチした専門分野: {matched_expertise}")
        
        can_handle = bool(matched_expertise)
        self.logger.info(f"処理可否: {can_handle}")
        
        if not can_handle:
            self.logger.info("-"*50)
            self.logger.info("タスクを処理できません")
            return None

        # ツールの選択
        self.logger.info("-"*50)
        self.logger.info("ツール選択を開始")
        self.logger.info(f"タスク内容: {task_description}")
        self.logger.info(f"利用可能なツール: {[tool.config.name for tool in self._tools.values()]}")
        
        selected_tools = []
        for tool in self._tools.values():
            # コード分析ツールは、コードが含まれる場合のみ選択
            if tool.config.name == "code_analysis":
                if "```" in original_query or "コード" in task_description.lower():
                    selected_tools.append(tool)
            else:
                selected_tools.append(tool)
        
        self.logger.info(f"選択されたツール: {[tool.config.name for tool in selected_tools]}")
        
        if not selected_tools:
            self.logger.info("実行可能なツールが見つかりません")
            return None

        # ツールの実行
        self.logger.info("-"*50)
        self.logger.info("ツールを使用したタスク実行を開始")
        
        self.logger.info("-"*50)
        self.logger.info("ツール実行フェーズを開始")
        self.logger.info(f"実行するツール数: {len(selected_tools)}")
        
        results = []
        for i, tool in enumerate(selected_tools, 1):
            self.logger.info(f"ツール {i}/{len(selected_tools)} の実行を開始: {tool.config.name}")
            
            self.logger.info(f"クエリ: {task_description}")
            self.logger.info(f"{tool.config.name}ツールを実行")
            
            try:
                # ツールの実行時にキーワード引数を使用
                if tool.config.name == "code_analysis":
                    # コードブロックの検出
                    code_blocks = self._extract_code_blocks(original_query)
                    if code_blocks:
                        result = await tool.execute(
                            query=task_description,
                            code=code_blocks[0],  # 最初のコードブロックを使用
                            language="python"  # デフォルトはPython
                        )
                    else:
                        self.logger.info("コードブロックは検出されませんでした")
                        continue
                else:
                    result = await tool.execute(query=task_description)
                
                if result:
                    results.append(f"{tool.config.name}: {result}")
            except Exception as e:
                self.logger.error(f"ツール {tool.config.name} の実行中にエラーが発生: {str(e)}")
                results.append(f"{tool.config.name}: エラーが発生しました - {str(e)}")

        if not results:
            return None

        # 結果の評価と統合
        self.logger.info("-"*50)
        self.logger.info("実行結果の評価を開始")
        self.logger.info("-"*50)
        self.logger.info("実行結果の評価を開始")
        self.logger.info(f"タスク内容: {task_description}")
        
        for result in results:
            self.logger.info(f"実行結果: {result}")
        
        self.logger.info("評価完了")
        self.logger.info("-"*50)
        self.logger.info("タスク実行が完了")
        self.logger.info("="*50)
        
        return "\n\n".join(results)

    def _extract_code_blocks(self, text: str) -> List[str]:
        """テキストからコードブロックを抽出"""
        import re
        pattern = r"```(?:[\w-]+\n)?(.*?)```"
        matches = re.finditer(pattern, text, re.DOTALL)
        return [match.group(1).strip() for match in matches if match.group(1).strip()]

    def get_capabilities(self) -> Set[str]:
        """現在の能力を取得"""
        return self._capabilities.copy()

    def get_tools(self) -> Dict[str, Tool]:
        """現在のツールを取得"""
        return self._tools.copy() 