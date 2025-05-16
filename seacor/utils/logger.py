import logging
import os

def get_logger(name: str) -> logging.Logger:
    """
    環境変数 SEACOR_LOG_LEVEL によってログレベルを設定し、
    ストリームハンドラーを付与したロガーを返します。
    デフォルトログレベルは INFO です。
    """
    # 環境変数からログレベルを取得（大文字化）
    level_str = os.getenv('SEACOR_LOG_LEVEL', 'INFO').upper()
    level = getattr(logging, level_str, logging.INFO)

    # ロガー取得
    logger = logging.getLogger(name)

    # ハンドラー未設定時にのみ設定を追加
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.setLevel(level)
    return logger
