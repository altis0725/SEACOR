from pydantic import BaseModel, Field
from typing import List, Dict, Any

class ExpertConfig(BaseModel):
    """
    エージェントの設定情報を保持するモデル
    """
    name: str
    layer: str
    expertise: List[str]
    goal: str
    backstory: str
    tools: List[str]

class ExpertsConfig(BaseModel):
    """
    専門家エージェント設定の一覧モデル
    """
    experts: List[ExpertConfig]

class ToolConfig(BaseModel):
    """
    ツール設定を保持するモデル
    """
    name: str
    module: str
    class_name: str = Field(..., alias='class')
    config: Dict[str, Any] = Field(default_factory=dict)

class ToolsConfig(BaseModel):
    """
    ツール設定の一覧モデル
    """
    tools: List[ToolConfig]

class LLMConfig(BaseModel):
    """
    LLM プロバイダーの設定モデル
    """
    provider: str
    model: str
    temperature: float = Field(..., ge=0.0, le=1.0)

class LoggingConfig(BaseModel):
    """
    ロギング設定モデル
    """
    level: str

class GrowthConfig(BaseModel):
    """
    自己進化ループのパラメータ設定モデル
    """
    min_confidence: float
    max_iterations: int
    learning_rate: float

class SeacorSettings(BaseModel):
    """
    グローバル設定モデル
    """
    version: str
    llm: LLMConfig
    logging: LoggingConfig
    growth: GrowthConfig