from seacor.utils.config_models import LLMConfig
from crewai import LLM, BaseLLM
from seacor.tools.monica_llm_tool import MonicaLLMTool

class LLMFactory:
    """
    LLMConfig に基づいて、CrewAI の BaseLLM インスタンスを返すファクトリ。
    """

    @staticmethod
    def get_llm(config: LLMConfig) -> LLM:
        provider = config.provider.lower()
        if provider == "monica_llm":
            # カスタム Monica AI プロバイダー
            return MonicaLLMTool(config)
        # それ以外は CrewAI 標準の汎用 LLM を使う
        # OPENAI_API_KEY 環境変数などは LLM 側で参照される
        return LLM(
            model=config.model,
            temperature=config.temperature,
            # 必要に応じて api_key_env="OPENAI_API_KEY" などを追加
        )