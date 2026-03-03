# config/settings.py
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent

class Config:
    """最终版配置（适配Ollama HTTP协议，无SSL干扰）"""
    # 基础路径
    TEMP_DIR = os.getenv("TEMP_DIR", str(BASE_DIR / "temp"))
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", str(BASE_DIR / "output"))
    
    # Whisper配置
    WHISPER_MODEL = os.getenv("WHISPER_MODEL", "large-v3")
    WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
    WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "ja")
    
    # OpenAI/Anthropic（备用）
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_API_BASE = os.getenv("ANTHROPIC_API_BASE", "https://api.anthropic.com/v1")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-haiku-20240307")
    
    # Ollama配置（核心：HTTP协议，无SSL）
    LOCAL_API_KEY = os.getenv("LOCAL_API_KEY", "ollama-no-key")  # 任意值即可
    LOCAL_API_BASE = os.getenv("LOCAL_API_BASE", "http://localhost:11434/v1")  # 必须是HTTP
    LOCAL_MODEL = os.getenv("LOCAL_MODEL", "gemma3:27b")
    
    # 翻译提供商
    TRANSLATION_PROVIDER = os.getenv("TRANSLATION_PROVIDER", "local")
    
    # 字幕配置（含缺失项）
    SUBTITLE_FONT = os.getenv("SUBTITLE_FONT", "Arial")
    SUBTITLE_FONT_SIZE = int(os.getenv("SUBTITLE_FONT_SIZE", 24))
    SUBTITLE_STROKE_WIDTH = int(os.getenv("SUBTITLE_STROKE_WIDTH", 2))
    SUBTITLE_ENCODING = os.getenv("SUBTITLE_ENCODING", "utf-8")
    SUBTITLE_MAX_CHARS_PER_LINE = int(os.getenv("SUBTITLE_MAX_CHARS_PER_LINE", 30))

config = Config()
__all__ = ["config"]











