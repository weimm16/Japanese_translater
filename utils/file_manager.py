# utils/file_manager.py
import shutil
import uuid
from pathlib import Path
from typing import Optional
from .logger import setup_logger

logger = setup_logger(__name__)

class FileManager:
    def __init__(self, temp_dir: str = "temp", output_dir: str = "output"):
        self.temp_dir = Path(temp_dir)
        self.output_dir = Path(output_dir)
        self.session_id = str(uuid.uuid4())[:8]
        
        # 创建目录
        self.temp_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)
        self.session_temp = self.temp_dir / self.session_id
        self.session_temp.mkdir(exist_ok=True)
        
        logger.info(f"Session temp dir: {self.session_temp}")
    
    def get_temp_path(self, filename: str) -> Path:
        return self.session_temp / filename
    
    def get_output_path(self, filename: str) -> Path:
        return self.output_dir / filename
    
    def cleanup_session(self):
        """清理临时文件"""
        if self.session_temp.exists():
            shutil.rmtree(self.session_temp)
            logger.info(f"Cleaned up session: {self.session_id}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup_session()
