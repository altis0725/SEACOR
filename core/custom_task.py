import logging
from crewai import Task
from pydantic import ValidationError
import inspect

class CustomTask(Task):
    def run(self, *args, **kwargs):
        max_retries = 2
        for attempt in range(max_retries + 1):
            query = self.description
            try:
                if isinstance(query, dict):
                    if "description" in query:
                        query = query["description"]
                    else:
                        caller = inspect.stack()[1]
                        logging.error(f"[CustomTask.run] dict型だがdescriptionフィールドなし: value={query}, 呼び出し元={caller.filename}:{caller.lineno}")
                        raise ValueError("Task descriptionがdict型ですがdescriptionフィールドがありません")
                elif not isinstance(query, str):
                    caller = inspect.stack()[1]
                    logging.error(f"[CustomTask.run] 想定外の型: type={type(query)}, value={query}, 呼び出し元={caller.filename}:{caller.lineno}")
                    raise TypeError(f"Task descriptionはstr型であるべきですが、{type(query)}型です")
            except (TypeError, ValueError) as e:
                caller = inspect.stack()[1]
                logging.error(f"[CustomTask.run] 型不一致エラー: {e}, value={query}, 呼び出し元={caller.filename}:{caller.lineno}")
                raise
            if hasattr(self.agent, "tools") and self.agent.tools:
                for tool in self.agent.tools:
                    try:
                        result = tool.run(query=query)
                        logging.info(f"[CustomTask] tooloutput: {result}")  # ファイルに記録
                        return result  # tooloutputをreturn
                    except ValidationError as e:
                        caller = inspect.stack()[1]
                        logging.error(f"[CustomTask.run] ValidationError: {e}, value={query}, 呼び出し元={caller.filename}:{caller.lineno}")
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
        return super().run(*args, **kwargs) 