import os
import requests
import logging
import json
from typing import Any, Dict
from crewai import LLM

MONICA_API_URL = os.getenv("MONICA_API_URL", "https://openapi.monica.im/v1")
MONICA_API_KEY = os.getenv("MONICA_API_KEY")
logger = logging.getLogger(__name__)

if not MONICA_API_KEY:
    raise RuntimeError("Missing MONICA_API_KEY environment variable")

HEADERS = {
    "Authorization": f"Bearer {MONICA_API_KEY}",
    "Content-Type": "application/json"
}

def ask_monica(
    prompt: str,
    model: str = None,
    temperature: float = None,
    max_tokens: int = 1024
) -> str:
    """
    MonicaAPI のチャット・コンプリーションを呼び出す
    """
    model = model or os.getenv("SEACOR_LLM_MODEL", "monica-3.5-32k")
    temperature = temperature if temperature is not None else float(os.getenv("SEACOR_LLM_TEMPERATURE", "0.7"))
    
    url = f"{MONICA_API_URL}/chat/completions"
    payload: Dict[str, Any] = {
        "model": model,
        # ChatCompletion 用メッセージ形式で
        "messages": [
            {"role": "system", "content": "You are Monica."},
            {"role": "user",   "content": prompt}
        ],
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    logger.info(f"Calling MonicaAPI {url} model={model} prompt_len={len(prompt)}")
    res = requests.post(url, headers=HEADERS, json=payload)
    logger.info(f"MonicaAPI status: {res.status_code}")
    res.raise_for_status()
    data = res.json()
    # choices の最初の message.content を返す
    return data["choices"][0]["message"]["content"]

class MonicaLLM(LLM):
    """CrewAI 用の MonicaAI LLM ラッパー"""
    AVAILABLE_MODELS = {
        "gpt-4o-mini": "高速で軽量なモデル。一般的なタスクに適しています。",
        "monica-3.5-32k": "バランスの取れた性能を持つモデル。複雑なタスクに適しています。",
        "claude-3-5-haiku-latest": "高度な推論能力を持つモデル。複雑な分析に適しています。"
    }

    def __init__(self, model: str = None, auto_select_model: bool = False):
        """
        Args:
            model: 使用するモデル名
            auto_select_model: Trueの場合、タスクに応じてモデルを自動選択
        """
        self.auto_select_model = auto_select_model
        self.model = model or os.getenv("MONICA_MODEL", "gpt-4o-mini")
        super().__init__(model=self.model)

    def _select_model_for_task(self, prompt: str) -> str:
        """タスクの内容に基づいて適切なモデルを選択"""
        model_selection_prompt = f"""
        以下のタスクに対して、最適なモデルを選択してください。
        利用可能なモデル:
        {json.dumps(self.AVAILABLE_MODELS, indent=2, ensure_ascii=False)}

        タスク:
        {prompt}

        モデルを1つだけ選択し、モデル名のみを返してください。
        """

        try:
            selected_model = ask_monica(
                model_selection_prompt,
                model="gpt-4o-mini",  # モデル選択には軽量なモデルを使用
                temperature=0.1  # 一貫性のある選択のために低い温度を設定
            ).strip()
            
            # 選択されたモデルが利用可能か確認
            if selected_model in self.AVAILABLE_MODELS:
                return selected_model
            logger.warning(f"選択されたモデル {selected_model} は利用できません。デフォルトモデルを使用します。")
            return self.model
        except Exception as e:
            logger.error(f"モデル選択中にエラーが発生: {e}")
            return self.model

    def call(self, prompt: str, **kwargs) -> str:
        if self.auto_select_model:
            selected_model = self._select_model_for_task(prompt)
            logger.info(f"タスクに基づいてモデル {selected_model} を選択しました")
            return ask_monica(prompt, model=selected_model)
        return ask_monica(prompt, model=self.model)
