import os
import requests
import asyncio
from crewai import BaseLLM
from seacor.utils.config_models import LLMConfig
from typing import Any, Dict, List, Optional, Union

class MonicaLLMTool(BaseLLM):
    """
    CrewAI の BaseLLM インターフェースに準拠した Monica AI プロバイダ。
    OpenAI 互換エンドポイント https://openapi.monica.im/v1/chat/completions を使用します。
    """

    name = "monica_llm"

    def __init__(self, config: LLMConfig):
        # BaseLLM 側で model_name と temperature を保持
        super().__init__(model=config.model, temperature=config.temperature)
        self.model_name = config.model
        self.api_key = os.getenv("MONICA_API_KEY")
        if not self.api_key:
            raise RuntimeError("MONICA_API_KEY が設定されていません")

    def call(
        self,
        messages: Union[str, List[Dict[str, str]]],
        tools: Optional[List[Dict[str, Any]]] = None,
        callbacks: Optional[List[Any]] = None,
        available_functions: Optional[Dict[str, Any]] = None,
    ) -> Union[str, Any]:
        """
        同期的に Monica AI の completions エンドポイントを呼び出し、応答を返す。
        """
        url = "https://openapi.monica.im/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        # messagesを純粋なdictリスト（role/contentのみ）に変換
        if isinstance(messages, str):
            payload_messages = [{"role": "user", "content": messages}]
        else:
            payload_messages = [
                {"role": m.get("role", "user"), "content": m.get("content", "")}
                for m in messages if isinstance(m, dict)
            ]

        body: Dict[str, Any] = {
            "model": self.model_name,
            "messages": payload_messages,
            "temperature": getattr(self, "temperature", 0.7),
        }
        # toolsやcallbacksはAPIに不要なのでbodyに含めない

        print("=== MonicaLLMTool call ===")
        print("URL:", url)
        print("Headers:", headers)
        print("Body:", body)

        resp = requests.post(url, json=body, headers=headers, timeout=30)
        print("Status:", resp.status_code)
        print("Response:", resp.text)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]

    def supports_function_calling(self) -> bool:
        return True

    def supports_stop_words(self) -> bool:
        return True

    def get_context_window_size(self) -> int:
        # エンドポイントが許容する最大コンテキスト長（例として 8192）
        return 8192

    def stream(
        self,
        messages: Union[str, List[Dict[str, str]]],
        stop: Optional[List[str]] = None,
        **kwargs
    ):
        """
        ストリーミングレスポンスをイテレータで返す。
        """
        url = "https://openapi.monica.im/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        if isinstance(messages, str):
            payload_messages = [{"role": "user", "content": messages}]
        else:
            payload_messages = messages

        body: Dict[str, Any] = {
            "model": self.model_name,
            "messages": payload_messages,
            "temperature": self.temperature,
            "stream": True,
            **kwargs,
        }
        if stop:
            body["stop"] = stop

        with requests.post(url, json=body, headers=headers, stream=True, timeout=30) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines(decode_unicode=True):
                if line:
                    yield line

    async def agenerate(self, prompts, **kwargs):
        # prompts: List[str]
        loop = asyncio.get_event_loop()
        def sync_call(prompt):
            return self.call(prompt)
        results = await asyncio.gather(*[loop.run_in_executor(None, sync_call, p) for p in prompts])
        # crewAIのOpenAI互換の戻り値形式に合わせる
        class DummyGen:
            def __init__(self, text): self.text = text
        return type('DummyResp', (), {
            'generations': [[DummyGen(r)] for r in results]
        })()