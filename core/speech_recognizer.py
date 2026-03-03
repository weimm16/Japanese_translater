# core/speech_recognizer.py
import whisper
import torch
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass
from utils.logger import setup_logger
from config.settings import config

logger = setup_logger(__name__)

@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str
    confidence: float

class SpeechRecognizer:
    def __init__(self, model_size: str = None, device: str = None):
        self.model_size = model_size or config.WHISPER_MODEL
        self.device = device or config.WHISPER_DEVICE
        
        # 检查CUDA可用性
        if self.device == "cuda" and not torch.cuda.is_available():
            logger.warning("CUDA not available, falling back to CPU")
            self.device = "cpu"
        
        logger.info(f"Loading Whisper model: {self.model_size} on {self.device}")
        self.model = whisper.load_model(self.model_size).to(self.device)
        logger.info("Whisper model loaded")
    
    def transcribe(self, audio_path: str, language: str = "ja") -> List[TranscriptSegment]:
        """
        识别语音并返回带时间戳的文本段
        """
        logger.info(f"Transcribing: {audio_path}")
        
        result = self.model.transcribe(
            audio_path,
            language=language,
            task="transcribe",
            verbose=False,
            condition_on_previous_text=True,
            # 约束每行最大字符数（Whisper内置参数）
          


            initial_prompt="""以下是日语对话的转录:""",  # 优化提示，强调日语特性

        )
        
        segments = []
        for seg in result["segments"]:
            segments.append(TranscriptSegment(
                start=seg["start"],
                end=seg["end"],
                text=seg["text"].strip(),
                confidence=seg.get("avg_logprob", 0.0)
            ))
        
        logger.info(f"Transcribed {len(segments)} segments")
        return segments
    
    def save_srt(self, segments: List[TranscriptSegment], output_path: str):
        """保存为SRT格式"""
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, seg in enumerate(segments, 1):
                start_time = self._format_time(seg.start)
                end_time = self._format_time(seg.end)
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{seg.text}\n\n")
    
    @staticmethod
    def _format_time(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds % 1) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"





