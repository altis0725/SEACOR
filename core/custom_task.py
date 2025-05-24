import logging
from crewai import Task
from pydantic import ValidationError

class CustomTask(Task):
    def run(self, *args, **kwargs):
        max_retries = 2
        for attempt in range(max_retries + 1):
            query = self.description
            if isinstance(query, dict):
                query = query.get("description", str(query))
            if hasattr(self.agent, "tools") and self.agent.tools:
                for tool in self.agent.tools:
                    try:
                        result = tool.run(query=query)
                        logging.info(f"[CustomTask] tooloutput: {result}")  # ファイルに記録
                        return result  # tooloutputをreturn
                    except ValidationError as e:
                        if attempt < max_retries:
                            error_msg = (
                                "\n【エラー】出力形式が正しくありません。指定されたJSON形式で再度出力してください。\n"
                                f"エラー詳細: {str(e)}"
                            )
                            self.description += error_msg
                            logging.warning(f"[CustomTask] ValidationError: {e} (retry {attempt+1})")
                        else:
                            logging.error(f"[CustomTask] ValidationError: {e} (final)")
                            raise
            # 既存のTaskのrunも呼び出す（必要なら）
        return super().run(*args, **kwargs) 