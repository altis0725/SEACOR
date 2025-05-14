from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from app.seacor.tools.llm_providers import LLMConfig, LLMFactory
import logging

logger = logging.getLogger(__name__)

class ToolConfig(BaseModel):
    """ツールの設定"""
    name: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    required_parameters: List[str] = Field(default_factory=list)
    llm_config: Optional[LLMConfig] = None

class Tool(ABC):
    """ツールの基底クラス"""
    def __init__(self, config: ToolConfig):
        self.config = config
        self._validate_config()
        self._llm = LLMFactory.get_llm(config.llm_config) if config.llm_config else None
        logger.info(f"ツール '{self.config.name}' を初期化しました")

    def _validate_config(self):
        """設定の検証"""
        for param in self.config.required_parameters:
            if param not in self.config.parameters:
                raise ValueError(f"Required parameter '{param}' not found in config")

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """ツールの実行"""
        pass

    def get_description(self) -> str:
        """ツールの説明を取得"""
        return self.config.description

    def get_parameters(self) -> Dict[str, Any]:
        """ツールのパラメータを取得"""
        return self.config.parameters

class WebSearchTool(Tool):
    """Web検索ツールの実装"""
    def __init__(self, llm_config: LLMConfig):
        super().__init__(ToolConfig(
            name="web_search",
            description="Web検索を実行し、関連情報を取得します",
            parameters={
                "query": "",
                "max_results": 5
            },
            required_parameters=["query"],
            llm_config=llm_config
        ))

    async def execute(self, **kwargs) -> str:
        """Web検索の実行（LLMを使用して情報を生成）"""
        query = kwargs.get("query", "")
        logger.info(f"WebSearchTool: クエリ '{query}' の処理を開始")
        
        if not query:
            logger.warning("WebSearchTool: クエリが空です")
            return "申し訳ありませんが、クエリの内容が空白になっています。具体的な検索クエリや調べたいテーマを教えていただけますでしょうか？"

        prompt = f"""
        以下のクエリに関連する情報を、Web検索結果のような形式で生成してください：
        {query}

        以下の形式で情報を提供してください：
        1. クエリに関連する主要な情報や事実
        2. 関連する具体的な例やケーススタディ
        3. 実用的なアドバイスや推奨事項

        情報は具体的で、実用的なものにしてください。
        """
        
        logger.info(f"WebSearchTool: LLMにクエリを送信")
        result = await self._llm.agenerate([prompt])
        logger.info(f"WebSearchTool: クエリ '{query}' の処理が完了")
        return result.generations[0][0].text

class CodeAnalysisTool(Tool):
    """コード分析ツールの実装"""
    def __init__(self, llm_config: LLMConfig):
        super().__init__(ToolConfig(
            name="code_analysis",
            description="コードを分析し、改善点を提案します",
            parameters={
                "query": "",
                "code": "",
                "language": "python",
                "analysis_type": "all"
            },
            required_parameters=["query"],
            llm_config=llm_config
        ))

    async def execute(self, **kwargs) -> str:
        """コード分析の実行（LLMを使用して分析を生成）"""
        query = kwargs.get("query", "")
        logger.info(f"CodeAnalysisTool: クエリ '{query}' の処理を開始")
        
        if not query:
            logger.warning("CodeAnalysisTool: クエリが空です")
            return "申し訳ありませんが、クエリの内容が空白になっています。分析したいコードや目的を教えていただけますでしょうか？"

        code = kwargs.get("code", "")
        if not code and "```" in query:
            logger.info("CodeAnalysisTool: クエリからコードブロックを抽出を試みます")
            import re
            code_blocks = re.findall(r"```(?:python)?\n(.*?)\n```", query, re.DOTALL)
            if code_blocks:
                code = code_blocks[0]
                logger.info("CodeAnalysisTool: コードブロックを抽出しました")

        if not code:
            logger.warning("CodeAnalysisTool: コードが空です")
            return "すみませんが、コードが空白のようです。分析するコードが提供されていないため、具体的な改善提案ができません。"

        language = kwargs.get("language", "python")
        prompt = f"""
        以下の{language}コードを分析し、改善点を提案してください：
        ```{language}
        {code}
        ```

        以下の観点から分析を行ってください：
        1. コードの品質（可読性、保守性）
        2. パフォーマンスの最適化
        3. セキュリティの考慮
        4. ベストプラクティスの適用

        具体的な改善案と、その理由を説明してください。
        """
        
        logger.info(f"CodeAnalysisTool: LLMにコード分析を依頼")
        result = await self._llm.agenerate([prompt])
        logger.info(f"CodeAnalysisTool: クエリ '{query}' の処理が完了")
        return result.generations[0][0].text 