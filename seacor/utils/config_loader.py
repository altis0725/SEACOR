import os
import yaml
from pathlib import Path
from typing import Dict, Any, List
from importlib import import_module

from seacor.utils.config_models import (
    ExpertsConfig,
    ExpertConfig,
    ToolsConfig,
    ToolConfig,
    SeacorSettings,
)

class ConfigLoader:
    """
    設定ディレクトリ内の YAML ファイルを読み込み、
    Pydantic モデルへパースするユーティリティクラス。
    """

    def __init__(self, config_dir: str):
        """
        Args:
            config_dir: 設定ファイル格納ディレクトリへのパス
        """
        self.config_dir = Path(config_dir)

    def load_experts(self) -> ExpertsConfig:
        """
        experts.yaml を読み込み、ExpertsConfig モデルを返す
        """
        path = self.config_dir / "experts.yaml"
        text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
        return ExpertsConfig(**data)

    def get_expert_configs(self) -> List[ExpertConfig]:
        """
        登録されている全 ExpertConfig のリストを返す
        """
        return self.load_experts().experts

    def load_tools(self) -> ToolsConfig:
        """
        tools.yaml を読み込み、ToolsConfig モデルを返す
        """
        path = self.config_dir / "tools.yaml"
        text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
        return ToolsConfig(**data)

    def get_tool_configs(self) -> List[ToolConfig]:
        """
        登録されている全 ToolConfig のリストを返す
        """
        return self.load_tools().tools

    def create_tools(self, llm_config: Any) -> Dict[str, Any]:
        """
        tools.yaml の定義に従ってツールインスタンスを生成・返却する。

        - module, class_name を動的 import
        - config 内 api_key_env を環境変数から取得して渡す
        - llm_config を渡せるコンストラクタには渡す
        """
        instances: Dict[str, Any] = {}
        for tc in self.get_tool_configs():
            module = import_module(tc.module)
            cls = getattr(module, tc.class_name)
            cfg = dict(tc.config)
            if "api_key_env" in cfg:
                cfg["api_key"] = os.getenv(cfg.pop("api_key_env"))
            try:
                # MonicaLLMToolの場合はllm_configのみ渡す
                if tc.class_name == "MonicaLLMTool":
                    inst = cls(llm_config)
                else:
                    inst = cls(**cfg, llm_config=llm_config)
            except TypeError:
                inst = cls(**cfg)
            instances[tc.name] = inst
        return instances

    def load_settings(self) -> SeacorSettings:
        """
        seacor-settings.yaml を読み込み、SeacorSettings モデルを返す
        """
        path = self.config_dir / "seacor-settings.yaml"
        text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(text)
        return SeacorSettings(**data)

    def get_settings(self) -> SeacorSettings:
        """
        load_settings のエイリアス
        """
        return self.load_settings()