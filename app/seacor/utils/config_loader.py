from typing import Dict, List, Any, Type, Optional
import yaml
from pathlib import Path
from pydantic import BaseModel
from app.seacor.tools.llm_providers import LLMConfig
from app.seacor.tools.base_tool import Tool, WebSearchTool, CodeAnalysisTool
from app.seacor.agents.expert_agent import ExpertConfig
from app.seacor.utils.logger import get_logger

logger = get_logger(__name__)

class ToolConfig(BaseModel):
    """ツール設定"""
    name: str
    description: str
    type: str
    config: Dict[str, Any]

class ExpertConfig(BaseModel):
    """専門家設定"""
    name: str
    expertise: List[str]
    goal: str
    backstory: str
    tools: List[str]

class SeacorConfig(BaseModel):
    """SEACOR全体の設定"""
    llm: Dict[str, Any]
    log_level: str
    log_file: str
    default_expertise: List[str]
    max_experts: int
    enabled_tools: List[str]
    cache_dir: str
    cache_ttl: int
    max_retries: int
    retry_delay: int
    timeout: int
    growth: Dict[str, float]
    knowledge_base: Dict[str, Any]
    security: Dict[str, Any]

class ConfigLoader:
    """設定ローダー"""
    def __init__(self, config_dir: str = "app/config"):
        """設定ローダーの初期化
        
        Args:
            config_dir: 設定ファイルのディレクトリパス。デフォルトは'app/config'
        """
        self.config_dir = Path(config_dir)
        self.logger = get_logger(f"{__name__}.ConfigLoader")
        self._tool_configs: Dict[str, ToolConfig] = {}
        self._expert_configs: List[ExpertConfig] = []
        self._seacor_config: Optional[SeacorConfig] = None
        self._load_configs()

    def _load_configs(self):
        """設定ファイルの読み込み"""
        self.logger.info("設定ファイルの読み込みを開始")
        
        # SEACOR設定の読み込み
        seacor_path = self.config_dir / "seacor.yaml"
        if seacor_path.exists():
            with open(seacor_path, "r", encoding="utf-8") as f:
                seacor_data = yaml.safe_load(f)
                self._seacor_config = SeacorConfig(**seacor_data)
            self.logger.info("SEACOR設定を読み込み")
        
        # ツール設定の読み込み
        tools_path = self.config_dir / "tools.yaml"
        if tools_path.exists():
            with open(tools_path, "r", encoding="utf-8") as f:
                tools_data = yaml.safe_load(f)
                for tool_name, tool_data in tools_data["tools"].items():
                    self._tool_configs[tool_name] = ToolConfig(**tool_data)
            self.logger.info(f"ツール設定を読み込み: {list(self._tool_configs.keys())}")
        
        # 専門家設定の読み込み
        experts_path = self.config_dir / "experts.yaml"
        if experts_path.exists():
            with open(experts_path, "r", encoding="utf-8") as f:
                experts_data = yaml.safe_load(f)
                for expert_data in experts_data["experts"]:
                    self._expert_configs.append(ExpertConfig(**expert_data))
            self.logger.info(f"専門家設定を読み込み: {[exp.name for exp in self._expert_configs]}")

    def get_seacor_config(self) -> Optional[SeacorConfig]:
        """SEACOR設定を取得"""
        return self._seacor_config

    def get_llm_config(self) -> Optional[LLMConfig]:
        """LLM設定を取得"""
        if not self._seacor_config:
            return None
        
        llm_data = self._seacor_config.llm
        return LLMConfig(
            provider=llm_data["provider"],
            model=llm_data["model"],
            temperature=llm_data["temperature"],
            max_tokens=llm_data["max_tokens"],
            timeout=llm_data["timeout"]
        )

    def create_tools(self, llm_config: LLMConfig) -> Dict[str, Tool]:
        """ツールのインスタンスを作成"""
        self.logger.info("ツールのインスタンス作成を開始")
        tools = {}
        
        tool_classes = {
            "CodeAnalysisTool": CodeAnalysisTool,
            "WebSearchTool": WebSearchTool,
            # 必要に応じて他のツールクラスを追加
        }
        
        for tool_name, tool_config in self._tool_configs.items():
            try:
                tool_class = tool_classes.get(tool_config.type)
                if not tool_class:
                    self.logger.warning(f"未定義のツールタイプ: {tool_config.type}")
                    continue
                
                # ツールの設定をLLM設定で更新
                tool_llm_config = llm_config.model_copy()
                for key, value in tool_config.config.items():
                    if hasattr(tool_llm_config, key):
                        setattr(tool_llm_config, key, value)
                
                # ツールのインスタンスを作成
                tool = tool_class(tool_llm_config)
                tools[tool_name] = tool
                self.logger.info(f"ツール '{tool_name}' を作成")
                
            except Exception as e:
                self.logger.error(f"ツール '{tool_name}' の作成中にエラー: {str(e)}")
        
        return tools

    def get_expert_configs(self) -> List[ExpertConfig]:
        """専門家設定を取得"""
        return self._expert_configs.copy()

    def get_tool_configs(self) -> Dict[str, ToolConfig]:
        """ツール設定を取得"""
        return self._tool_configs.copy() 