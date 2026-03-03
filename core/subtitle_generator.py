# core/subtitle_generator.py
import re
from pathlib import Path
from typing import List, Dict
from config.settings import config
from utils.logger import setup_logger

logger = setup_logger(__name__)

class SubtitleGenerator:
    """字幕生成器，支持SRT/ASS格式"""
    def __init__(self):
        # 容错：如果配置项不存在，使用默认值30
        self.max_chars_per_line = getattr(config, "SUBTITLE_MAX_CHARS_PER_LINE", 30)
        self.font = config.SUBTITLE_FONT
        self.font_size = config.SUBTITLE_FONT_SIZE
        self.stroke_width = config.SUBTITLE_STROKE_WIDTH
        self.encoding = config.SUBTITLE_ENCODING

    def _split_long_text(self, text: str) -> str:
        """将长文本按每行最大字符数拆分（适配配置项）"""
        if len(text) <= self.max_chars_per_line:
            return text
        
        # 按标点/空格拆分，避免截断单词
        words = re.split(r'([，。！？；、 ])', text)
        lines = []
        current_line = ""
        
        for word in words:
            if len(current_line + word) <= self.max_chars_per_line:
                current_line += word
            else:
                if current_line:
                    lines.append(current_line.strip())
                current_line = word
        
        if current_line:
            lines.append(current_line.strip())
        
        return "\n".join(lines)

    def create_srt(self, segments: List[Dict], output_path: str):
        """生成SRT格式字幕"""
        output_path = Path(output_path)
        logger.info(f"生成SRT字幕: {output_path}")
        
        with open(output_path, "w", encoding=self.encoding) as f:
            for idx, seg in enumerate(segments, 1):
                # 格式化时间（SRT格式：00:00:00,000 --> 00:00:05,000）
                start = self._format_time(seg["start"])
                end = self._format_time(seg["end"])
                # 拆分长文本
                text = self._split_long_text(seg.get("translation", seg["text"]))
                
                f.write(f"{idx}\n")
                f.write(f"{start} --> {end}\n")
                f.write(f"{text}\n\n")

    def create_ass(self, segments: List[Dict], output_path: str):
        """生成ASS格式字幕（支持样式）"""
        output_path = Path(output_path)
        logger.info(f"生成ASS字幕: {output_path}")
        
        # ASS文件头部（包含样式定义）
        ass_header = f"""[Script Info]
Title: Translated Subtitles
ScriptType: v4.00+
WrapStyle: 0
ScaledBorderAndShadow: yes
Collisions: Normal

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{self.font},{self.font_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,0,0,0,0,100,100,0,0,1,{self.stroke_width},0,2,10,10,30,0

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        
        with open(output_path, "w", encoding=self.encoding) as f:
            f.write(ass_header)
            
            for seg in segments:
                start = self._format_ass_time(seg["start"])
                end = self._format_ass_time(seg["end"])
                # 拆分长文本
                text = self._split_long_text(seg.get("translation", seg["text"]))
                # 替换ASS特殊字符
                text = self._escape_ass_chars(text)
                
                f.write(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}\n")

    def _format_time(self, seconds: float) -> str:
        """将秒数格式化为SRT时间（00:00:00,000）"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        ms = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"

    def _format_ass_time(self, seconds: float) -> str:
        """将秒数格式化为ASS时间（0:00:00.00）"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        cs = int((seconds - int(seconds)) * 100)
        return f"{hours}:{minutes:02d}:{secs:02d}.{cs:02d}"

    def _escape_ass_chars(self, text: str) -> str:
        """转义ASS特殊字符"""
        escape_map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '\\': '\\',
            '{': '\\{',
            '}': '\\}'
        }
        for char, replacement in escape_map.items():
            text = text.replace(char, replacement)
        return text

# 测试代码
if __name__ == "__main__":
    generator = SubtitleGenerator()
    # 测试数据
    test_segments = [
        {"start": 0.0, "end": 5.0, "text": "こんにちは、世界！今日は天気が非常に良いですね、外に出かけるのに最適な日です。"},
        {"start": 5.0, "end": 10.0, "text": "私はPythonプログラミングが好きで、字幕生成のプロジェクトを作っています。"}
    ]
    # 生成SRT/ASS
    generator.create_srt(test_segments, "test.srt")
    generator.create_ass(test_segments, "test.ass")
    logger.info("测试字幕生成完成")
