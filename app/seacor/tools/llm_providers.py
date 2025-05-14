from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import requests  # httpxの代わりにrequestsを使用
import json
import os
import logging
import asyncio
from functools import partial
import subprocess
import httpx

class LLMProvider(str, Enum):
    """LLMプロバイダーの種類"""
    MONICA = "monica"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    # 必要に応じて他のプロバイダーを追加

class LLMConfig(BaseModel):
    """LLM設定"""
    provider: LLMProvider = Field(default_factory=lambda: LLMProvider(os.getenv("SEACOR_LLM_PROVIDER", "monica")))
    model: str = Field(default_factory=lambda: os.getenv("SEACOR_LLM_MODEL", "gpt-4o-mini"))
    temperature: float = Field(default_factory=lambda: float(os.getenv("SEACOR_LLM_TEMPERATURE", "0.7")))
    max_tokens: int = Field(default=2000)
    timeout: int = Field(default=30)

class MonicaAIProvider:
    """Monica AIプロバイダー"""
    def __init__(self, config: LLMConfig):
        self.config = config
        self.api_key = os.getenv("MONICA_API_KEY")
        if not self.api_key:
            raise ValueError("MONICA_API_KEY環境変数が設定されていません")
        
        self.base_url = "https://openapi.monica.im/v1"
        self._stop = None
        self._headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def bind(self, stop=None, **kwargs):
        """crewaiのインターフェースに必要なbindメソッド"""
        self._stop = stop
        return self

    async def agenerate(self, prompts: List[str]) -> Any:
        """非同期テキスト生成（crewai用, httpxベース）"""
        logger = logging.getLogger(__name__)

        try:
            results = []
            async with httpx.AsyncClient(timeout=self.config.timeout) as client:
                for prompt in prompts:
                    system_message = "You are a helpful AI assistant."
                    if self._stop:
                        system_message += f"\nStop when you see: {self._stop}"

                    # モデル名の正規化
                    model = self.config.model

                    request_body = {
                        "model": model,
                        "messages": [
                            {"role": "system", "content": system_message},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": self.config.temperature,
                        "max_tokens": self.config.max_tokens,
                        "stream": False
                    }
                    logger.info(f"Monica AI API Request Body: {request_body}")

                    res = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=self._headers,
                        json=request_body
                    )
                    logger.info(f"MonicaAI status: {res.status_code}")
                    res.raise_for_status()
                    result = res.json()
                    logger.info(f"Monica AI API Response: {result}")
                    if "choices" not in result:
                        logger.error(f"Monica API error response: {result}")
                        raise Exception(f"Monica API error response: {result}")
                    results.append({
                        "text": result["choices"][0]["message"]["content"],
                        "generation_info": {
                            "finish_reason": result["choices"][0].get("finish_reason", "stop"),
                            "prompt_tokens": result.get("usage", {}).get("prompt_tokens", 0),
                            "completion_tokens": result.get("usage", {}).get("completion_tokens", 0),
                            "total_tokens": result.get("usage", {}).get("total_tokens", 0)
                        }
                    })
            from langchain.schema import Generation, LLMResult
            generations = [[Generation(text=r["text"], generation_info=r["generation_info"])] for r in results]
            return LLMResult(generations=generations)
        except Exception as e:
            logger.error(f"Error in MonicaAIProvider.agenerate: {str(e)}")
            raise Exception(f"Monica AI APIエラー: {str(e)}")

    async def generate(self, prompt: str) -> str:
        """テキスト生成（後方互換性用）"""
        result = await self.agenerate([prompt])
        return result.generations[0][0].text

    async def close(self):
        """クライアントのクローズ（requestsでは不要）"""
        pass

    def __call__(self, prompt: str, **kwargs):
        """Runnable互換: 同期呼び出し用"""
        import asyncio
        return asyncio.run(self.generate(prompt))

    def invoke(self, prompt: str, **kwargs):
        """Runnable互換: langchain用"""
        return self.__call__(prompt, **kwargs)

class LLMFactory:
    """LLMインスタンスの生成を管理"""
    _instances: Dict[str, Any] = {}

    @classmethod
    def get_llm(cls, config: LLMConfig) -> Any:
        """設定に基づいてLLMインスタンスを取得"""
        key = f"{config.provider}:{config.model}"
        if key not in cls._instances:
            cls._instances[key] = cls._create_llm(config)
        return cls._instances[key]

    @staticmethod
    def _create_llm(config: LLMConfig) -> Any:
        """LLMインスタンスの作成"""
        if config.provider == LLMProvider.MONICA:
            return MonicaAIProvider(config)
        elif config.provider == LLMProvider.OPENAI:
            from langchain.chat_models import ChatOpenAI
            return ChatOpenAI(
                model_name=config.model,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                **config.additional_params
            )
        elif config.provider == LLMProvider.ANTHROPIC:
            from langchain.chat_models import ChatAnthropic
            return ChatAnthropic(
                model=config.model,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
                **config.additional_params
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {config.provider}")

    @staticmethod
    def create_provider(config: LLMConfig):
        """プロバイダーの作成"""
        if config.provider == LLMProvider.MONICA:
            return MonicaAIProvider(config)
        else:
            raise ValueError(f"未対応のプロバイダー: {config.provider}") 