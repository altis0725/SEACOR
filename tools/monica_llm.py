from typing import Optional
import os
import requests
import logging

class MonicaLLM:
    def __init__(self, api_key=None, endpoint=None, model=None, temperature=0.7, max_tokens=2000):
        self.api_key = api_key or os.environ.get("MONICA_API_KEY")
        self.endpoint = endpoint or "https://openapi.monica.im/v1/"
        self.model = model or "gpt-4o"
        self.temperature = temperature
        self.max_tokens = max_tokens

    def call(self, prompt: str, system_message: Optional[str] = None, **kwargs) -> str:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        messages = []
        if system_message:
            messages.append({"role": "system", "content": system_message})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }
        logging.info("=== MonicaAI APIリクエスト ===")
        logging.info(f"endpoint: {self.endpoint}")
        logging.info(f"headers: {headers}")
        logging.info(f"payload: {payload}")
        logging.info("===========================")
        response = requests.post(self.endpoint, headers=headers, json=payload)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]

# 例: 
# llm = MonicaLLM()
# result = llm.call("こんにちは、自己紹介してください")
# print(result) 