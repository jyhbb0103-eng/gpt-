"""项目配置。所有可调整参数集中放在这里。"""

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # 允许在尚未安装依赖时运行纯评分测试
    def load_dotenv(*_args, **_kwargs):
        return False


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat").strip()
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip()

DATA_TIMEOUT_SECONDS = int(os.getenv("DATA_TIMEOUT_SECONDS", "20"))
LLM_TIMEOUT_SECONDS = int(os.getenv("LLM_TIMEOUT_SECONDS", "45"))

LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "dabao_market_agent.log"

INDEXES = {
    "上证指数": "sh000001",
    "深证成指": "sz399001",
    "创业板指": "sz399006",
    "沪深300": "csi000300",
}


def setup_logging():
    """初始化控制台和文件日志，并返回项目 logger。"""
    import logging
    from logging.handlers import RotatingFileHandler

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("dabao_market_agent")
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s", "%Y-%m-%d %H:%M:%S"
    )
    file_handler = RotatingFileHandler(
        LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    return logger
