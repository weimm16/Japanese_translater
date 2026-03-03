# utils/logger.py
import logging
import sys
from pathlib import Path
from datetime import datetime

def setup_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    # 控制台输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    
    # 文件输出（优化权限+跨平台路径）
    log_dir = Path("logs")
    try:
        log_dir.mkdir(exist_ok=True, mode=0o755)
    except PermissionError:
        # 权限不足时，使用用户主目录
        log_dir = Path.home() / "Japanese_translater_logs"
        log_dir.mkdir(exist_ok=True, mode=0o755)
    
    file_handler = logging.FileHandler(
        log_dir / f"{datetime.now():%Y%m%d_%H%M%S}.log",
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(console_format)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

