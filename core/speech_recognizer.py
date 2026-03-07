# core/speech_recognizer.py
import whisper
import torch
from pathlib import Path
from typing import List, Dict, Any
from dataclasses import dataclass
from utils.logger import setup_logger
from config.settings import config

# 延迟导入，避免启动时加载
_soundfile = None
_WhisperProcessor = None
_WhisperForConditionalGeneration = None

def _lazy_imports():
    global _soundfile, _WhisperProcessor, _WhisperForConditionalGeneration
    if _soundfile is None:
        import soundfile as sf
        _soundfile = sf
    if _WhisperProcessor is None or _WhisperForConditionalGeneration is None:
        from transformers import WhisperForConditionalGeneration, WhisperProcessor
        _WhisperProcessor = WhisperProcessor
        _WhisperForConditionalGeneration = WhisperForConditionalGeneration
    return _soundfile, _WhisperProcessor, _WhisperForConditionalGeneration

logger = setup_logger(__name__)

@dataclass
class TranscriptSegment:
    start: float
    end: float
    text: str
    confidence: float

class SpeechRecognizer:
    def __init__(self, model_size: str = None, device: str = None, progress_callback: callable = None):
        self.model_size = model_size or config.WHISPER_MODEL
        self.device = device or config.WHISPER_DEVICE
        self.is_kotoba = self.model_size == "kotoba-whisper"
        self.processor = None
        self.progress_callback = progress_callback
        
        # 检查CUDA可用性
        if self.device == "cuda" and not torch.cuda.is_available():
            logger.warning("CUDA not available, falling back to CPU")
            self.device = "cpu"
        
        if self.is_kotoba:
            logger.info(f"准备加载kotoba-whisper模型 on {self.device}")
            # 延迟加载模型，在transcribe时才实际下载
            self.model = None
        else:
            logger.info(f"Loading Whisper model: {self.model_size} on {self.device}")
            self.model = whisper.load_model(self.model_size).to(self.device)
            logger.info("Whisper model loaded")
    
    def transcribe(self, audio_path: str, language: str = "ja") -> List[TranscriptSegment]:
        """
        识别语音并返回带时间戳的文本段
        """
        logger.info(f"Transcribing: {audio_path}")
        
        if self.is_kotoba:
            # 使用kotoba-whisper模型进行转录
            try:
                # 延迟导入必要的库
                sf, WhisperProcessor, WhisperForConditionalGeneration = _lazy_imports()
                
                # 加载模型（首次使用时下载）
                if self.model is None or self.processor is None:
                    logger.info("Downloading and loading kotoba-whisper model...")
                    
                    # 定义进度回调函数
                    def download_progress_callback(step, total, status):
                        logger.info(f"Downloading: {status} - {step}/{total}")
                        if self.progress_callback:
                            # 计算进度百分比（10% 作为模型下载的占比）
                            progress = (step / total) * 10
                            self.progress_callback(1, 100)  # 发送进度更新
                    
                    # 下载并加载模型
                    self.processor = WhisperProcessor.from_pretrained("kotaemon/kotoba-whisper", progress_callback=download_progress_callback)
                    self.model = WhisperForConditionalGeneration.from_pretrained("kotaemon/kotoba-whisper", progress_callback=download_progress_callback).to(self.device)
                    logger.info("kotoba-whisper model loaded")
                    # 模型下载完成，更新进度
                    if self.progress_callback:
                        self.progress_callback(10, 100)
                
                # 读取音频
                audio, sr = sf.read(audio_path)
                logger.info(f"Audio loaded: {len(audio)} samples, {sr} Hz")
                
                # 处理音频
                input_features = self.processor(audio, sampling_rate=sr, return_tensors="pt").input_features.to(self.device)
                logger.info("Audio processed for model input")
                
                # 生成转录
                predicted_ids = self.model.generate(
                    input_features,
                    language=language,
                    task="transcribe",
                    max_new_tokens=255,
                    return_timestamps=True
                )
                logger.info("Transcription generated")
                
                # 解码结果
                result = self.processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
                logger.info(f"Decoded result: {result[:100]}...")
                
                # 由于kotoba-whisper的返回格式与原始whisper不同，这里需要处理
                # 简化处理，将整个音频作为一个段
                segments = [TranscriptSegment(
                    start=0.0,
                    end=len(audio)/sr,
                    text=result.strip(),
                    confidence=0.0
                )]
                logger.info(f"Created {len(segments)} segments")
            except Exception as e:
                logger.error(f"Error with kotoba-whisper: {e}")
                # 出错时使用原始whisper模型作为备份
                logger.info("Falling back to original whisper model")
                self.is_kotoba = False
                self.model = whisper.load_model("large-v3").to(self.device)
                return self.transcribe(audio_path, language)
        else:
            # 使用原始whisper模型
            result = self.model.transcribe(
                audio_path,
                language=language,
                task="transcribe",
                verbose=False,
                condition_on_previous_text=True,
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