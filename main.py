# main.py
import asyncio
import argparse
import sys
from pathlib import Path
from typing import Optional, Callable
from config.settings import config
from utils.logger import setup_logger
from utils.file_manager import FileManager
from core.audio_extractor import AudioExtractor
from core.speech_recognizer import SpeechRecognizer
from core.translator import LLMTranslator
from core.subtitle_generator import SubtitleGenerator
from core.video_renderer import VideoRenderer

logger = setup_logger(__name__)
# 定义总处理步骤（用于进度计算）
TOTAL_STEPS = 4  # 提取音频→语音识别→翻译→烧录字幕

class VideoTranslator:
    def __init__(self):
        self.file_manager = FileManager(config.TEMP_DIR, config.OUTPUT_DIR)
        # 自动创建输出/临时目录，解决路径不存在问题
        Path(config.TEMP_DIR).mkdir(exist_ok=True, parents=True)
        Path(config.OUTPUT_DIR).mkdir(exist_ok=True, parents=True)
        self.audio_extractor = AudioExtractor()
        self.speech_recognizer = None  # 延迟加载
        self.translator = LLMTranslator()
        self.subtitle_generator = SubtitleGenerator()
        self.video_renderer = VideoRenderer()

    async def process(self, video_path: str,
                      output_name: Optional[str] = None,
                      skip_translate: bool = False,
                      burn_subtitles: bool = True,
                      source_language: str = "ja",
                      progress_callback: Callable[[int, int], None] = None) -> dict:
        """
        处理视频的主流程
        :param progress_callback: 进度回调函数 (当前步骤, 总步骤)
        """
        video_path = Path(video_path)
        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        if output_name is None:
            output_name = f"{video_path.stem}_translated.mp4"
        # 强制转为绝对路径，避免相对路径保存混乱
        output_name = Path(output_name).absolute()

        results = {
            'video_path': str(video_path),
            'audio_path': None,
            'transcript_path': None,
            'translation_path': None,
            'subtitle_path': None,
            'output_path': None
        }

        try:
            current_step = 1
            # 1. 提取音频 + 进度回调
            logger.info("Step 1: Extracting audio...")
            if progress_callback:
                progress_callback(current_step, TOTAL_STEPS)
            audio_path = self.file_manager.get_temp_path("audio.wav")
            self.audio_extractor.extract(str(video_path), str(audio_path))
            results['audio_path'] = str(audio_path)
            current_step += 1

            # 2. 语音识别 + 进度回调
            logger.info(f"Step 2: Speech recognition ({source_language})...")
            if progress_callback:
                progress_callback(current_step, TOTAL_STEPS)
            if self.speech_recognizer is None:
                self.speech_recognizer = SpeechRecognizer()

            segments = self.speech_recognizer.transcribe(str(audio_path), language=source_language)

            # 保存原始转录（绝对路径）
            transcript_path = self.file_manager.get_temp_path("original.srt")
            self.speech_recognizer.save_srt(segments, str(transcript_path))
            results['transcript_path'] = str(transcript_path)
            current_step += 1

            # 3. 翻译 + 进度回调
            if not skip_translate:
                logger.info("Step 3: Translating...")
                if progress_callback:
                    progress_callback(current_step, TOTAL_STEPS)
                # 转换为字典列表
                seg_dicts = [{"start": s.start, "end": s.end, "text": s.text} for s in segments]
                translations = await self.translator.translate_batch(seg_dicts, source_language=source_language)

                # 生成翻译字幕（绝对路径，自定义输出名）
                srt_name = f"{output_name.stem}_cn.srt"
                ass_name = f"{output_name.stem}_cn.ass"
                srt_path = output_name.parent / srt_name
                ass_path = output_name.parent / ass_name

                self.subtitle_generator.create_srt(translations, str(srt_path))
                self.subtitle_generator.create_ass(translations, str(ass_path))

                results['translation_path'] = str(srt_path)
                results['subtitle_path'] = str(ass_path)
                current_step += 1

                # 4. 烧录字幕到视频 + 进度回调
                if burn_subtitles:
                    logger.info("Step 4: Burning subtitles to video...")
                    if progress_callback:
                        progress_callback(current_step, TOTAL_STEPS)
                    self.video_renderer.burn_subtitles(
                        str(video_path),
                        str(ass_path),  # 使用ASS格式以获得更好效果
                        str(output_name)
                    )
                    results['output_path'] = str(output_name)
            else:
                logger.info("Translation skipped")
                # 跳过翻译时，进度直接拉满
                if progress_callback:
                    progress_callback(TOTAL_STEPS, TOTAL_STEPS)

            logger.info("Processing completed!")
            return results

        except Exception as e:
            logger.error(f"Processing failed: {e}")
            raise
        finally:
            # 无论成功/失败，都清理临时文件，解决磁盘残留问题
            self.cleanup()

    def cleanup(self):
        """清理临时文件"""
        self.file_manager.cleanup_session()
        logger.info("临时文件已清理")

async def main():
    parser = argparse.ArgumentParser(description='多语言视频翻译工具')
    parser.add_argument('video', help='输入视频文件路径')
    parser.add_argument('-o', '--output', help='输出文件名/绝对路径', default=None)
    parser.add_argument('--skip-translate', action='store_true', help='跳过翻译，仅生成原始字幕')
    parser.add_argument('--no-burn', action='store_true', help='不烧录字幕，仅生成字幕文件')
    parser.add_argument('--model', help='Whisper模型大小', default='large-v3')
    parser.add_argument('--device', help='运行设备', default='cuda')
    parser.add_argument('--language', help='源语言代码 (ja, en, ko, es, fr, de, it, pt, ru, ar, hi, th, vi)', default='ja')

    args = parser.parse_args()

    # 更新配置
    config.WHISPER_MODEL = args.model
    config.WHISPER_DEVICE = args.device
    config.WHISPER_LANGUAGE = args.language

    translator = VideoTranslator()

    try:
        results = await translator.process(
            args.video,
            output_name=args.output,
            skip_translate=args.skip_translate,
            burn_subtitles=not args.no_burn,
            source_language=args.language
        )

        print("\n" + "="*50)
        print("处理完成！")
        print(f"原始字幕: {results['transcript_path']}")
        if results['translation_path']:
            print(f"中文字幕(SRT): {results['translation_path']}")
            print(f"中文字幕(ASS): {results['subtitle_path']}")
        if results['output_path']:
            print(f"输出视频: {results['output_path']}")
        print("="*50)

    except KeyboardInterrupt:
        print("\n用户取消")
    except Exception as e:
        logger.error(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # 优化事件循环创建（兼容Windows）
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if "asyncio.run() cannot be called from a running event loop" in str(e):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(main())
        else:
            raise