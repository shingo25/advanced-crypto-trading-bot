import logging
from datetime import datetime
from pathlib import Path

from rich.logging import RichHandler

from src.backend.core.config import settings


def setup_logging():
    """ロギングをセットアップ"""
    # ログディレクトリを作成
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)

    # ログレベルを設定
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # ログフォーマット
    log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # ルートロガーの設定
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # 既存のハンドラーをクリア
    root_logger.handlers.clear()

    # コンソールハンドラー（Rich）
    console_handler = RichHandler(rich_tracebacks=True, tracebacks_show_locals=True)
    console_handler.setLevel(log_level)
    root_logger.addHandler(console_handler)

    # ファイルハンドラー
    log_file = log_dir / f"crypto_bot_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(log_level)
    file_formatter = logging.Formatter(log_format)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # 外部ライブラリのログレベルを調整
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    root_logger.info(f"Logging initialized. Level: {settings.LOG_LEVEL}, File: {log_file}")
