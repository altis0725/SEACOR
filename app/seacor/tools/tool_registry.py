import os
import requests
from typing import Any, Dict
from app.seacor.factories.yaml_handler import YamlHandler

class ToolRegistry:
    """
    外部ツールへの呼び出しを管理するレジストリ。
    config/tools.yaml を読み込み、crew からの呼び出しを仲介。
    """
    def __init__(self):
        self.yaml = YamlHandler(config_dir=os.path.join(os.path.dirname(__file__), '..', 'config'))
        self.tools = self.yaml.read_yaml('tools.yaml').get('tools', {})

    def call_tool(self, tool_id: str, params: Dict[str, Any]) -> Any:
        """
        指定ツールIDのエンドポイントへリクエストを投げる。
        """
        tool = self.tools.get(tool_id)
        if not tool:
            raise ValueError(f"Unknown tool: {tool_id}")
        endpoint = tool.get('endpoint')
        response = requests.post(endpoint, json=params)
        response.raise_for_status()
        return response.json()
