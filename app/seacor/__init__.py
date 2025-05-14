"""
SEACOR (Self-Evolving Autonomous Crew of Experts and Resources)
自律的に進化する専門家とリソースのクルーシステム
"""

from app.seacor.utils.logger import get_logger
from app.seacor.utils.config_loader import ConfigLoader
from app.seacor.agents.expert_agent import ExpertAgent
from app.seacor.crews.expert_crew import ExpertCrew
from app.seacor.tools.base_tool import Tool
from app.seacor.tools.llm_providers import LLMConfig

__version__ = "0.1.0"

# ルートロガーの設定
logger = get_logger(__name__)

# パッケージの公開インターフェース
__all__ = [
    "ExpertAgent",
    "ExpertCrew",
    "Tool",
    "LLMConfig",
    "ConfigLoader",
    "get_logger",
    "logger",
    "__version__",
] 