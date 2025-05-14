from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
from typing import List, Dict, Optional
import asyncio
import json
from app.seacor.utils.config import ConfigManager
from app.seacor.crews.expert_crew import ExpertCrew
from app.seacor.tools.base_tool import WebSearchTool, CodeAnalysisTool
from app.seacor.utils.logger import get_logger

# ロガーの設定
logger = get_logger()

app = FastAPI(title="SEACOR API")

# CORS設定
config = ConfigManager()
allowed_origins = config.config.security.allowed_origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静的ファイルのマウント
app.mount("/static", StaticFiles(directory="app/static"), name="static")

class SeacorApp:
    """SEACORアプリケーション（API用）"""
    def __init__(self):
        self.config = ConfigManager()
        self.logger = self.config.get_logger("seacor")
        self.crew: Optional[ExpertCrew] = None
        
        # LLM設定の取得
        llm_conf = self.config.get_llm_config()
        
        # ExpertCrewの初期化
        self.crew = ExpertCrew(llm_config=llm_conf)
        self.logger.info("SeacorAppを初期化しました")

    async def initialize(self):
        """アプリケーションの初期化"""
        try:
            self.logger.info("SEACORアプリケーションの初期化が完了しました")
        except Exception as e:
            self.logger.error(f"初期化中にエラーが発生しました: {e}")
            raise

    async def process_query(self, query: str) -> str:
        """クエリの処理"""
        self.logger.info(f"クエリの処理を開始: {query}")
        try:
            result = await self.crew.process_query(query)
            self.logger.info("クエリの処理が完了しました")
            return result
        except Exception as e:
            self.logger.error(f"クエリの処理中にエラーが発生しました: {str(e)}")
            raise

# WebSocket接続管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.seacor_app = SeacorApp()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info("connection open")

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info("connection closed")

    async def send_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

manager = ConnectionManager()

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            message = await websocket.receive_text()
            logger.info(f"Received message: {message}")
            try:
                result = await manager.seacor_app.process_query(message)
                # レスポンスをJSON形式に変換
                response = {
                    "type": "response",
                    "content": result,
                    "status": "success"
                }
                await manager.send_message(json.dumps(response, ensure_ascii=False), websocket)
            except Exception as e:
                error_message = f"クエリの処理中にエラーが発生しました: {str(e)}"
                logger.error(error_message)
                # エラーレスポンスもJSON形式に
                error_response = {
                    "type": "error",
                    "content": error_message,
                    "status": "error"
                }
                await manager.send_message(json.dumps(error_response, ensure_ascii=False), websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/")
async def root():
    """ルートパスにindex.htmlを提供"""
    return FileResponse("app/static/index.html")

@app.get("/api/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {"status": "healthy"}

@app.get("/api/config")
async def get_config():
    """設定情報の取得"""
    return {
        "llm": config.config.llm.dict(),
        "enabled_tools": config.config.enabled_tools,
        "max_experts": config.config.max_experts
    } 