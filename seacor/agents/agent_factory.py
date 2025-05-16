from crewai import Agent
from seacor.utils.config_models import ExpertConfig
from seacor.tools.llm_providers import LLMConfig, LLMFactory
from typing import Dict, Any

def create_expert_agent(
    cfg: ExpertConfig,
    llm_config: LLMConfig,
    tools_map: Dict[str, Any]
) -> Agent:
    """
    ExpertConfig から CrewAI Agent インスタンスを生成します。
    ────────────────────────────────────────
    ・tools_map から必要なツールインスタンス一覧を作成
    ・LLM を wrap して llm, function_calling_llm に渡す
    ・Agent コンストラクタに role, goal, backstory, llm, tools を渡すだけ
    """
    print(f"[create_expert_agent] name={cfg.name} layer={cfg.layer} expertise={cfg.expertise}")
    # cfg.toolsがNoneの場合も考慮
    tool_names = cfg.tools if cfg.tools is not None else []
    print(f"[create_expert_agent] tool_names={tool_names}")
    # 指定されたツール名に対応するツールインスタンスを取得
    tool_instances = [
        tools_map[name] for name in tool_names if name in tools_map
    ]
    print(f"[create_expert_agent] tool_instances={tool_instances}")
    llm = LLMFactory.get_llm(llm_config)
    print(f"[create_expert_agent] llm={llm}")
    agent = Agent(
        role="/".join(cfg.expertise),
        goal=cfg.goal,
        backstory=cfg.backstory,
        llm=llm,
        # ツール呼び出し用 LLM を同じものにする場合
        function_calling_llm=llm,
        tools=tool_instances,  # 必ず明示的に渡す
        #parser=parser,
        allow_delegation=False,
        verbose=True,
    )
    agent.config = cfg  # 追加: エージェントに設定情報を持たせる
    print(f"[create_expert_agent] Agent created: {agent}")
    return agent