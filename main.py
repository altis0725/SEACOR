import uvicorn
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os
import logging
import json
import re

from crews.generic_crew import kickoff_async_crew
from utils.yaml_loader import reencode_json_to_utf8
from utils.evolution_applier import apply_evolution

# ログ設定（アプリ全体で一度だけ）
logging.basicConfig(
    filename='logs/task.log',
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s'
)

app = FastAPI()

# publicディレクトリのパス
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PUBLIC_DIR = os.path.join(BASE_DIR, "public")

# logsディレクトリがなければ作成
os.makedirs("logs", exist_ok=True)

# 静的ファイルを/staticでマウント
app.mount("/static", StaticFiles(directory=PUBLIC_DIR, html=True), name="static")

@app.post("/v1/chat/completions")
async def chat_completions(request: Request, background_tasks: BackgroundTasks):
    """
    OpenAI互換: POST /v1/chat/completions
    リクエスト例:
    {
      "model": "gpt-4o-mini",
      "messages": [
        {"role": "system", "content": "..."},
        {"role": "user", "content": "..."}
      ],
      "temperature": 0.7,
      "max_tokens": 2000
    }
    """
    data = await request.json()
    messages = data.get("messages", [])
    prompt = ""
    system_message = ""
    # OpenAI互換: system, user, assistantのroleを考慮
    for msg in messages:
        if msg["role"] == "system":
            system_message = msg["content"]
        elif msg["role"] == "user":
            prompt += msg["content"] + "\n"

    # main_crewのみkickoff
    main_result = await kickoff_async_crew("main_crew", prompt.strip(), system_message.strip())
    # main_crewの最終回答（revise_taskの出力）を取得
    main_final_answer = getattr(main_result, "raw", str(main_result))
    reencode_json_to_utf8("logs/meta_crew.json")

    # evolution_crew, flow_review_crewはバックグラウンドで実行
    async def run_background_crews(main_final_answer, prompt):
        evolution_result = await kickoff_async_crew("evolution_crew", prompt, system_message=main_final_answer)
        reencode_json_to_utf8("logs/evolution_crew.json")
        # 進化案を自動適用（詳細ログ付き）
        try:
            evo_json = getattr(evolution_result, "raw", str(evolution_result))
            logging.info("[進化案自動適用] evolution_result.raw:")
            logging.info(evo_json)
            match = re.search(r'Final Answer:\s*({.*})', evo_json, re.DOTALL)
            if match:
                json_str = match.group(1)
                logging.info("[進化案自動適用] 抽出したJSON:")
                logging.info(json_str)
                try:
                    evo = json.loads(json_str)
                    logging.info("[進化案自動適用] パース成功。内容:")
                    logging.info(json.dumps(evo, ensure_ascii=False, indent=2))
                    apply_evolution(evo)
                except Exception as e:
                    logging.error(f"[進化案自動適用エラー] JSONパース失敗: {e}")
            else:
                # Final Answer: が無い場合、全体をJSONとしてパースを試みる
                try:
                    evo = json.loads(evo_json)
                    logging.info("[進化案自動適用] Final Answer無し。全体をパース成功。内容:")
                    logging.info(json.dumps(evo, ensure_ascii=False, indent=2))
                    apply_evolution(evo)
                except Exception as e:
                    logging.error(f"[進化案自動適用エラー] Final Answer無し・全体パース失敗: {e}")
        except Exception as e:
            logging.error(f"[進化案自動適用エラー] {e}")
        flow_review_result = await kickoff_async_crew("flow_review_crew", prompt, system_message=main_final_answer)
        reencode_json_to_utf8("logs/flow_review_crew.json")

    background_tasks.add_task(run_background_crews, main_final_answer, prompt)

    # main_crewの出力のみを返す
    content = main_final_answer
    response = {
        "id": "chatcmpl-xxxxxx",
        "object": "chat.completion",
        "created": 0,
        "model": data.get("model", "gpt-4o-mini"),
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
    }
    return JSONResponse(content=response)

@app.get("/")
def root():
    return FileResponse(os.path.join(PUBLIC_DIR, "index.html"))

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 