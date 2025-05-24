from typing import Optional
from crewai.tools import BaseTool
import os
import requests
import json
import logging
from pydantic import BaseModel, Field

logging.basicConfig(filename='logs/task.log', level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')

class MonicaLLMSchema(BaseModel):
    query: str | dict = Field(..., description="ユーザーからの入力")
    system_message: str | None = Field(default=None, description="システムメッセージ")

class MonicaLLM(BaseTool):
    name: str = "Monica LLM"
    description: str = "MonicaAI LLM APIラッパー"
    api_key: str = ""
    endpoint: str = "https://openapi.monica.im/v1/chat/completions"
    model: str = "gpt-4o-mini"
    temperature: float = 0.7
    max_tokens: int = 2000
    args_schema = MonicaLLMSchema

    def __init__(self, api_key=None, endpoint=None, model=None, temperature=0.7, max_tokens=2000, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key or os.environ.get("MONICA_API_KEY") or self.api_key
        self.endpoint = endpoint or self.endpoint
        self.model = model or self.model
        self.temperature = temperature if temperature is not None else self.temperature
        self.max_tokens = max_tokens if max_tokens is not None else self.max_tokens

    def _run(self, query: str | dict = "", system_message: str | None = None):
        # dict型ならdescriptionだけ抽出
        if isinstance(query, dict):
            query = query.get("description", str(query))
        if isinstance(system_message, dict):
            system_message = system_message.get("description", str(system_message))
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": query})
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        # デバッグ用: 実際にMonicaAIに渡す内容を出力
        logging.info("=== MonicaAI APIリクエスト ===")
        logging.info(f"endpoint: {self.endpoint}")
        logging.info(f"headers: {headers}")
        logging.info(f"payload: {payload}")
        logging.info("===========================")
        response = requests.post(self.endpoint, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

    def chat(self, messages, **kwargs):
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens)
        }
        response = requests.post(self.endpoint, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()

# 例: 
# llm = MonicaLLM()
# result = llm.chat_completion("こんにちは、自己紹介してください")
# print(result["choices"][0]["message"]["content"]) 