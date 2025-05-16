from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
import uvicorn

from seacor.utils.config_loader import ConfigLoader
from seacor.tools.llm_providers import LLMConfig
from seacor.crews.expert_crew import ExpertCrew

app = FastAPI()

# 静的ファイルを /static にマウント
app.mount("/static", StaticFiles(directory="seacor/public", html=True), name="public")

# ルート('/')でindex.htmlを返す
@app.get("/")
def root():
    return FileResponse("seacor/public/index.html")

# 設定の読み込み
config_loader = ConfigLoader("seacor/config")
settings = config_loader.load_settings()
llm_config = settings.llm

# ExpertCrew のインスタンス化
expert_crew = ExpertCrew(llm_config=llm_config, config_dir="seacor/config")

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    reply: str

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    reply_text = await expert_crew.process_query(request.message)
    return ChatResponse(reply=reply_text)

@app.get("/health")
def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("seacor.__main__:app", host="0.0.0.0", port=8000, reload=True)