# core/video_renderer.py
import ffmpeg
import subprocess
import shutil
import codecs
from pathlib import Path
from typing import Optional, Tuple
from utils.logger import setup_logger
from config.settings import config

logger = setup_logger(__name__)

def check_ffmpeg():
    """检查FFmpeg是否安装并在PATH中"""
    if shutil.which("ffmpeg") is None:
        raise EnvironmentError("未找到FFmpeg！请先安装并添加到系统PATH")

class VideoRenderer:
    def __init__(self):
        check_ffmpeg()  # 初始化时检查FFmpeg
        self.font_path = self._get_font_path()
        # 校验字体文件是否存在
        if self.font_path and not Path(self.font_path).exists():
            logger.warning(f"指定的字体文件不存在：{self.font_path}，可能导致字幕显示异常")

    def burn_subtitles(self, video_path: str, subtitle_path: str,
                       output_path: str,
                       style: Optional[dict] = None) -> str:
        """
        将字幕烧录到视频中（修复音频丢失+字幕缺失问题）
        """
        # === 核心修复1：严格校验输入文件 ===
        video_path = Path(video_path)
        subtitle_path = Path(subtitle_path)
        output_path = Path(output_path)

        # 校验视频文件
        if not video_path.exists():
            raise FileNotFoundError(f"视频文件不存在：{video_path}")
        if not video_path.is_file():
            raise ValueError(f"视频路径不是有效文件：{video_path}")
        # 校验字幕文件
        if not subtitle_path.exists():
            raise FileNotFoundError(f"字幕文件不存在：{subtitle_path}")
        if subtitle_path.stat().st_size < 10:  # 空/极小字幕文件
            raise ValueError(f"字幕文件为空或损坏：{subtitle_path}")
        # 校验字幕编码（默认UTF-8，兼容GBK）
        self._check_subtitle_encoding(subtitle_path)

        logger.info(f"Burning subtitles: {video_path} -> {output_path}")

        # 构建字幕样式（修复style格式问题）
        if style is None:
            style = {
                'Fontname': config.SUBTITLE_FONT,
                'Fontsize': str(config.SUBTITLE_FONT_SIZE),  # 强制转字符串，避免数字类型错误
                'PrimaryColour': '&H00FFFFFF',
                'OutlineColour': '&H00000000',
                'Outline': str(config.SUBTITLE_STROKE_WIDTH),
                'Alignment': '2',
                'MarginV': '30'
            }
        # 修复：过滤空值/非法键，避免style_str拼接错误
        style_str = ','.join([f"{k}={v}" for k, v in style.items() if v and isinstance(v, (str, int))])

        try:
            # 1. 获取原始视频信息（修复异常处理）
            probe = ffmpeg.probe(str(video_path))
            video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
            audio_stream = next((s for s in probe['streams'] if s['codec_type'] == 'audio'), None)
            video_duration = float(probe['format']['duration']) if 'duration' in probe['format'] else 0

            if not video_stream:
                raise Exception("输入视频中未找到视频流")

            # === 核心修复2：校验字幕时间轴（避免超出视频时长的字幕被忽略） ===
            self._check_subtitle_timeline(subtitle_path, video_duration)

            # 2. 构建FFmpeg命令（修复字幕滤镜参数）
            input_stream = ffmpeg.input(str(video_path))
            subtitle_input = ffmpeg.input(str(subtitle_path))  # 独立加载字幕流，提升兼容性

            # 应用字幕滤镜
            if subtitle_path.suffix.lower() == '.ass':
                # ASS字幕：指定字体路径，修复字体缺失导致的字幕不显示
                ass_filter_kwargs = {'filename': str(subtitle_path)}
                if self.font_path:
                    ass_filter_kwargs['fontsdir'] = str(Path(self.font_path).parent)  # 字体目录
                video = ffmpeg.filter(input_stream['v'], 'ass', **ass_filter_kwargs)
            else:
                # SRT字幕：修复force_style传递方式，增加编码指定
                sub_filter_kwargs = {
                    'filename': str(subtitle_path),
                    'force_style': style_str,
                    'charenc': 'utf-8'  # 强制指定字幕编码，避免乱码/解析失败
                }
                video = ffmpeg.filter(input_stream['v'], 'subtitles', **sub_filter_kwargs)

            # 3. 输出设置（保留音频修复）
            output_kwargs = {
                'vcodec': 'libx264',
                'acodec': 'aac',
                'video_bitrate': '5M',
                'audio_bitrate': '192k',
                'preset': 'medium',
                'crf': 23,
                'movflags': '+faststart',
                'loglevel': 'warning'  # 保留FFmpeg警告日志，便于定位字幕问题
            }

            # 处理音频流
            if audio_stream:
                output = ffmpeg.output(
                    video,
                    input_stream['a'],
                    str(output_path),
                    **output_kwargs
                )
            else:
                logger.warning("输入视频中未找到音频流，输出视频将无声")
                output = ffmpeg.output(
                    video,
                    str(output_path),
                    **output_kwargs
                )

            # 4. 执行FFmpeg命令（捕获详细错误日志）
            try:
                ffmpeg.run(output, overwrite_output=True, quiet=False, capture_stderr=True)
            except ffmpeg.Error as e:
                # 解析FFmpeg stderr日志，定位字幕滤镜错误
                stderr = e.stderr.decode('utf-8', errors='ignore') if e.stderr else ""
                logger.error(f"FFmpeg字幕烧录错误：{stderr}")
                raise RuntimeError(f"FFmpeg执行失败：{stderr}") from e

            logger.info(f"Video rendered: {output_path}")
            return str(output_path)

        except Exception as e:
            logger.error(f"Rendering error: {e}", exc_info=True)  # 打印完整堆栈，便于调试
            raise

    def extract_frame(self, video_path: str, time: float, output_path: str):
        """提取预览帧（修复quiet=True导致的调试缺失）"""
        try:
            stream = ffmpeg.input(video_path, ss=time, vframes=1)
            stream = ffmpeg.output(stream, output_path)
            # 取消quiet=True，保留帧提取错误日志
            ffmpeg.run(stream, overwrite_output=True, quiet=False)
        except Exception as e:
            logger.error(f"提取预览帧失败（时间点：{time}）：{e}")
            raise

    def get_video_info(self, video_path: str) -> Tuple[int, int, float]:
        """获取视频信息（修复未捕获的StopIteration异常）"""
        try:
            probe = ffmpeg.probe(video_path)
            video_stream = next((s for s in probe['streams'] if s['codec_type'] == 'video'), None)
            if not video_stream:
                raise ValueError("视频中未找到视频流")
            width = int(video_stream['width'])
            height = int(video_stream['height'])
            duration = float(probe['format']['duration']) if 'duration' in probe['format'] else 0.0
            return width, height, duration
        except StopIteration:
            raise ValueError("视频中未找到视频流")
        except Exception as e:
            logger.error(f"获取视频信息失败：{e}")
            raise

    def _get_font_path(self) -> Optional[str]:
        """获取系统字体路径（兼容更多Linux字体）"""
        import platform
        system = platform.system()

        if system == "Windows":
            font_path = Path("C:/Windows/Fonts/msyh.ttc")
            return str(font_path) if font_path.exists() else None
        elif system == "Darwin":  # macOS
            font_path = Path("/System/Library/Fonts/PingFang.ttc")
            return str(font_path) if font_path.exists() else None
        else:  # Linux
            # 兼容更多Linux发行版的中文字体
            font_paths = [
                "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
            ]
            for path in font_paths:
                if Path(path).exists():
                    return path
            return None

    def _check_subtitle_encoding(self, subtitle_path: Path):
        """校验并修复字幕文件编码（避免乱码/解析失败）"""
        try:
            # 尝试UTF-8读取
            with codecs.open(subtitle_path, 'r', 'utf-8') as f:
                f.read(1024)
        except UnicodeDecodeError:
            # 尝试GBK读取并转换为UTF-8
            try:
                with codecs.open(subtitle_path, 'r', 'gbk') as f:
                    content = f.read()
                # 重新写入为UTF-8
                with codecs.open(subtitle_path, 'w', 'utf-8') as f:
                    f.write(content)
                logger.warning(f"字幕文件 {subtitle_path} 为GBK编码，已自动转换为UTF-8")
            except Exception as e:
                raise ValueError(f"字幕文件编码不支持（非UTF-8/GBK）：{subtitle_path}，错误：{e}")

    def _check_subtitle_timeline(self, subtitle_path: Path, video_duration: float):
        """校验字幕时间轴是否超出视频时长（避免字幕被FFmpeg忽略）"""
        if video_duration <= 0:
            return  # 无法获取视频时长，跳过校验
        if subtitle_path.suffix.lower() not in ['.srt', '.ass']:
            return  # 仅校验常见字幕格式

        try:
            # 简易解析SRT/ASS时间轴（核心：检查字幕结束时间是否超出视频时长）
            content = subtitle_path.read_text(encoding='utf-8')
            if subtitle_path.suffix.lower() == '.srt':
                # 匹配SRT时间轴：00:00:01,000 --> 00:00:05,000
                import re
                time_pattern = re.compile(r'(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})')
                matches = time_pattern.findall(content)
                for start_time, end_time in matches:
                    # 转换end_time为秒数
                    h, m, s_ms = end_time.split(':')
                    s, ms = s_ms.split(',')
                    end_seconds = int(h)*3600 + int(m)*60 + int(s) + int(ms)/1000
                    if end_seconds > video_duration + 1:  # 允许1秒误差
                        logger.warning(f"字幕时间轴超出视频时长：{end_time}（视频时长：{video_duration:.2f}秒），该字幕可能被忽略")
            # ASS字幕可按需扩展解析逻辑
        except Exception as e:
            logger.warning(f"校验字幕时间轴失败（不影响执行）：{e}")






