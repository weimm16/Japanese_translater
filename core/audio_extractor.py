# core/audio_extractor.py
import ffmpeg
import subprocess
import shutil
from pathlib import Path
from typing import Optional
from utils.logger import setup_logger

logger = setup_logger(__name__)

def check_ffmpeg():
    """检查FFmpeg是否安装并在PATH中"""
    if shutil.which("ffmpeg") is None:
        raise EnvironmentError("未找到FFmpeg！请先安装并添加到系统PATH")

class AudioExtractor:
    def __init__(self, sample_rate: int = 16000):
        check_ffmpeg()  # 初始化时检查FFmpeg
        self.sample_rate = sample_rate
    
    def extract(self, video_path: str, output_path: Optional[str] = None) -> str:
        """
        从视频中提取音频
        """
        video_path = Path(video_path)
        if output_path is None:
            output_path = video_path.with_suffix('.wav')
        else:
            output_path = Path(output_path)
        
        logger.info(f"Extracting audio from {video_path}")
        
        try:
            # 使用ffmpeg提取音频
            stream = ffmpeg.input(str(video_path))
            stream = ffmpeg.output(
                stream, 
                str(output_path),
                ac=1,  # 单声道
                ar=self.sample_rate,  # 采样率
                vn=None,  # 无视频
                acodec='pcm_s16le'  # 16位PCM
            )
            ffmpeg.run(stream, overwrite_output=True, quiet=True)
            
            logger.info(f"Audio extracted: {output_path}")
            return str(output_path)
            
        except ffmpeg.Error as e:
            logger.error(f"FFmpeg error: {e.stderr.decode() if e.stderr else str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error extracting audio: {e}")
            raise
