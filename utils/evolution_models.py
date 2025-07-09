from pydantic import BaseModel, Field
from typing import List, Optional

class AgentDefinition(BaseModel):
    role: str
    goal: str
    backstory: str
    llm: str = "monica_llm"
    verbose: bool = True

class MergeAgentDefinition(BaseModel):
    from_: List[str] = Field(..., alias="from")
    to: str
    definition: AgentDefinition

class EvolutionOutput(BaseModel):
    new_agents: Optional[List[AgentDefinition]] = []
    remove_agents: Optional[List[str]] = []
    merge_agents: Optional[List[MergeAgentDefinition]] = []
    # 必要に応じて他のフィールドも追加 