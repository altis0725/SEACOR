import asyncio
import argparse
import sys
from typing import Optional
from app.seacor.utils.config import ConfigManager
from app.seacor.tools.base_tool import WebSearchTool, CodeAnalysisTool
from app.seacor.crews.expert_crew import ExpertCrew
from app.api import app  # api.pyのアプリケーションをインポート
from app.seacor.utils.logger import get_logger

# ロガーの設定
logger = get_logger(__name__)

class SeacorApp:
    """SEACORアプリケーション"""
    def __init__(self):
        self.config = ConfigManager()
        self.logger = self.config.get_logger("seacor")
        self.crew: Optional[ExpertCrew] = None
    
    def initialize(self):
        """アプリケーションの初期化"""
        try:
            # ツールの初期化
            tools = self._initialize_tools()
            
            # ExpertCrewの初期化
            self.crew = ExpertCrew(
                llm_config=self.config.get_llm_config(),
                tools=tools
            )
            
            self.logger.info("SEACORアプリケーションの初期化が完了しました")
            
        except Exception as e:
            self.logger.error(f"初期化中にエラーが発生しました: {e}")
            raise
    
    def _initialize_tools(self) -> list:
        """ツールの初期化"""
        tools = []
        enabled_tools = self.config.config.enabled_tools
        
        # デフォルトのツール
        default_tools = {
            "web_search": WebSearchTool,
            #"code_analysis": CodeAnalysisTool
        }
        
        # 有効なツールの初期化
        for tool_name in enabled_tools:
            if tool_class := default_tools.get(tool_name):
                try:
                    tools.append(tool_class())
                    self.logger.info(f"ツール '{tool_name}' を初期化しました")
                except Exception as e:
                    self.logger.error(f"ツール '{tool_name}' の初期化に失敗しました: {e}")
        
        return tools
    
    async def process_query(self, query: str) -> str:
        """クエリの処理"""
        if not self.crew:
            raise RuntimeError("アプリケーションが初期化されていません")
        
        try:
            self.logger.info(f"クエリの処理を開始: {query}")
            result = await self.crew.process_query(query)
            self.logger.info("クエリの処理が完了しました")
            return result
            
        except Exception as e:
            self.logger.error(f"クエリの処理中にエラーが発生しました: {e}")
            raise

async def main():
    """メインエントリーポイント"""
    # コマンドライン引数の解析
    parser = argparse.ArgumentParser(description="SEACOR: Self-Evolving Agent Crew for Objective Reasoning")
    parser.add_argument("query", nargs="?", help="処理するクエリ")
    parser.add_argument("--config", help="設定ファイルのパス")
    parser.add_argument("--interactive", action="store_true", help="対話モードで実行")
    args = parser.parse_args()
    
    try:
        # アプリケーションの初期化
        app_instance = SeacorApp()
        app_instance.initialize()
        
        if args.interactive:
            # 対話モード
            print("SEACOR対話モードを開始します（終了するには 'exit' または 'quit' と入力）")
            while True:
                try:
                    query = input("\nクエリを入力してください: ").strip()
                    if query.lower() in ("exit", "quit"):
                        break
                    if not query:
                        continue
                    
                    result = await app_instance.process_query(query)
                    print("\n結果:")
                    print(result)
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"エラー: {e}")
            
        elif args.query:
            # 単一クエリの処理
            result = await app_instance.process_query(args.query)
            print(result)
            
        else:
            parser.print_help()
            sys.exit(1)
            
    except Exception as e:
        print(f"エラー: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

# FastAPIアプリケーションのイベントハンドラ
@app.on_event("startup")
async def startup_event():
    """アプリケーション起動時の処理"""
    logger.info("アプリケーションを起動します")

@app.on_event("shutdown")
async def shutdown_event():
    """アプリケーション終了時の処理"""
    logger.info("アプリケーションを終了します")
