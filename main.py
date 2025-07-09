import uvicorn
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import os
import logging
from dotenv import load_dotenv
import debugpy

from crews.generic_crew import kickoff_async_crew
from utils.yaml_loader import reencode_json_to_utf8

load_dotenv()
LOG_FILE = os.environ.get("LOG_FILE", "logs/task.log")
logging.basicConfig(
    filename=LOG_FILE,
    level=getattr(logging, os.getenv("SEACOR_LOG_LEVEL", "INFO")),
    format='%(asctime)s %(levelname)s %(name)s %(message)s'
)

def enable_debug():
    """デバッグモードを有効化"""
    debugpy.listen(("0.0.0.0", 5678))
    print("デバッガー待機中: 0.0.0.0:5678")
    # デバッガーが接続するまで待機
    debugpy.wait_for_client()
    print("デバッガー接続完了")

# デバッグモードの初期化を先に行う
print("環境変数 PYTHONBREAKPOINT:", os.getenv("PYTHONBREAKPOINT"))
if os.getenv("PYTHONBREAKPOINT") == "0":
    enable_debug()

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
    try:
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
        # main_crewの最終回答を取得
        main_final_answer = getattr(main_result, "raw", str(main_result))
        reencode_json_to_utf8("logs/main_crew.json")

        # evolution_crew, flow_review_crewはバックグラウンドで実行
        # async def run_background_crews(main_final_answer: str, prompt: str):
        #     try:
        #         # evolution_crewの実行
        #         evolution_result = await kickoff_async_crew(
        #             "evolution_crew", 
        #             prompt, 
        #             system_message=main_final_answer
        #         )
        #         reencode_json_to_utf8("logs/evolution_crew.json")
                
        #         # flow_review_crewの実行
        #         flow_review_result = await kickoff_async_crew(
        #             "flow_review_crew", 
        #             prompt, 
        #             system_message=main_final_answer
        #         )
        #         reencode_json_to_utf8("logs/flow_review_crew.json")
                
        #     except Exception as e:
        #         logging.error(f"バックグラウンドクルー実行エラー: {e}")

        # # バックグラウンドタスクとして実行
        # background_tasks.add_task(run_background_crews, main_final_answer, prompt)

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
        
    except Exception as e:
        logging.error(f"chat_completionsエラー: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": str(e)}
        )

@app.get("/")
def root():
    return FileResponse(os.path.join(PUBLIC_DIR, "index.html"))

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)  # デバッグモードとの競合を避けるためreload=False 