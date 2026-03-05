# utils/config_saver.py
import json
import os
from pathlib import Path
from utils.logger import setup_logger

logger = setup_logger(__name__)
# 配置保存路径（跨平台绝对路径）
CONFIG_FILE = Path(__file__).resolve().parent.parent / "gui_config.json"

def save_gui_config(config: dict):
    """保存GUI配置到json文件"""
    try:
        # 确保目录存在
        CONFIG_FILE.parent.mkdir(exist_ok=True, parents=True)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4, ensure_ascii=False)
        logger.info(f"GUI配置已保存到: {CONFIG_FILE}")
    except Exception as e:
        logger.warning(f"保存配置失败: {e}")

def load_gui_config(default: dict = None) -> dict:
    """加载GUI配置，无配置时返回默认值"""
    if default is None:
        default = {"model": "large-v3", "api": "openai", "language": "ja - 日语", "burn_subtitles": True}
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                config = json.load(f)
            # 补全缺失的配置项
            for k, v in default.items():
                config.setdefault(k, v)
            logger.info(f"从{CONFIG_FILE}加载GUI配置")
            return config
    except Exception as e:
        logger.warning(f"加载配置失败，使用默认值: {e}")
    return default