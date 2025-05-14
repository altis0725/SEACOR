import logging
import sys
from typing import Dict

# ロガーのキャッシュ
_logger_cache: Dict[str, logging.Logger] = {}

def setup_logger(name: str = None) -> logging.Logger:
    """ロガーの設定
    
    Args:
        name: ロガー名。Noneの場合はルートロガーを返す
        
    Returns:
        logging.Logger: 設定済みのロガー
    """
    # キャッシュをチェック
    if name in _logger_cache:
        return _logger_cache[name]
    
    # ロガーの取得
    logger = logging.getLogger(name)
    
    # ルートロガーの場合、またはハンドラーが未設定の場合のみ設定を行う
    if name is None or not logger.handlers:
        # ログレベルの設定
        logger.setLevel(logging.INFO)
        
        # 既存のハンドラーをクリア
        logger.handlers.clear()
        
        # ハンドラーの設定
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(logging.INFO)
        
        # フォーマッターの設定
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        # ハンドラーの追加
        logger.addHandler(handler)
        
        # 親ロガーへの伝播を無効化
        logger.propagate = False
    
    # キャッシュに保存
    _logger_cache[name] = logger
    
    return logger

def get_logger(name: str = None) -> logging.Logger:
    """既存のロガーを取得または新規作成
    
    Args:
        name: ロガー名。Noneの場合はルートロガーを返す
        
    Returns:
        logging.Logger: ロガー
    """
    return setup_logger(name) 