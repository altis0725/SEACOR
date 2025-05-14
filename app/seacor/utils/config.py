from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from pathlib import Path
import os
import yaml
import logging
from app.seacor.tools.llm_providers import LLMConfig, LLMProvider

class SecurityConfig(BaseModel):
    """セキュリティ設定"""
    api_key_required: bool = True
    rate_limit: int = 100
    allowed_origins: List[str] = Field(default_factory=lambda: ["*"])

class SeacorConfig(BaseModel):
    """SEACORの設定"""
    # LLM設定
    llm: LLMConfig = Field(
        default_factory=lambda: LLMConfig(
            provider=LLMProvider(os.getenv("SEACOR_LLM_PROVIDER", "monica")),
            model=os.getenv("SEACOR_LLM_MODEL", "monica-3.5-32k"),
            temperature=float(os.getenv("SEACOR_LLM_TEMPERATURE", "0.7"))
        )
    )
    
    # ログ設定
    log_level: str = "INFO"
    log_file: Optional[str] = "seacor.log"
    
    # 専門家設定
    default_expertise: list[str] = Field(default_factory=list)
    max_experts: int = 10
    
    # ツール設定
    enabled_tools: list[str] = Field(default_factory=list)
    
    # セキュリティ設定
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    
    # その他の設定
    cache_dir: str = ".cache"
    max_retries: int = 3
    timeout: int = 30

class ConfigManager:
    """設定管理クラス"""
    _instance = None
    _config: Optional[SeacorConfig] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._config is None:
            self._load_config()
            self._setup_logging()
    
    def _load_config(self):
        """設定の読み込み"""
        # 環境変数から設定を読み込み
        env_config = self._load_from_env()
        
        # 設定ファイルから設定を読み込み
        file_config = self._load_from_file()
        
        # 設定のマージ
        config_dict = {**file_config, **env_config}
        self._config = SeacorConfig(**config_dict)
    
    def _load_from_env(self) -> Dict[str, Any]:
        """環境変数から設定を読み込み"""
        config = {}
        
        # LLM設定はSeacorConfigのデフォルト値で一元管理
        # その他の設定
        if log_level := os.getenv("SEACOR_LOG_LEVEL"):
            config["log_level"] = log_level
        if log_file := os.getenv("SEACOR_LOG_FILE"):
            config["log_file"] = log_file
        
        # セキュリティ設定
        security_config = {}
        if api_key_required := os.getenv("SEACOR_SECURITY_API_KEY_REQUIRED"):
            security_config["api_key_required"] = api_key_required.lower() == "true"
        if rate_limit := os.getenv("SEACOR_SECURITY_RATE_LIMIT"):
            security_config["rate_limit"] = int(rate_limit)
        if allowed_origins := os.getenv("SEACOR_SECURITY_ALLOWED_ORIGINS"):
            security_config["allowed_origins"] = allowed_origins.split(",")
        if security_config:
            config["security"] = security_config
        
        # その他の設定
        if max_experts := os.getenv("SEACOR_MAX_EXPERTS"):
            config["max_experts"] = int(max_experts)
        if max_retries := os.getenv("SEACOR_MAX_RETRIES"):
            config["max_retries"] = int(max_retries)
        if timeout := os.getenv("SEACOR_TIMEOUT"):
            config["timeout"] = int(timeout)
        
        return config
    
    def _load_from_file(self) -> Dict[str, Any]:
        """設定ファイルから設定を読み込み"""
        config_paths = [
            Path("config/seacor.yaml"),
            Path("config/seacor.yml"),
            Path("seacor.yaml"),
            Path("seacor.yml"),
        ]
        
        for path in config_paths:
            if path.exists():
                try:
                    with open(path) as f:
                        return yaml.safe_load(f)
                except Exception as e:
                    logging.warning(f"設定ファイルの読み込みに失敗: {path}, {e}")
        
        return {}
    
    def _setup_logging(self):
        """ログ設定"""
        log_config = {
            "level": getattr(logging, self._config.log_level),
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        }
        
        if self._config.log_file:
            log_config["filename"] = self._config.log_file
            log_config["filemode"] = "a"
        
        logging.basicConfig(**log_config)
    
    @property
    def config(self) -> SeacorConfig:
        """現在の設定を取得"""
        return self._config
    
    def get_llm_config(self) -> LLMConfig:
        """LLM設定を取得"""
        return self._config.llm
    
    def get_logger(self, name: str) -> logging.Logger:
        """ロガーを取得"""
        return logging.getLogger(name)
    
    def reload(self):
        """設定の再読み込み"""
        self._load_config()
        self._setup_logging() 