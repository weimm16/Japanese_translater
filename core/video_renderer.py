import ffmpeg
import subprocess
import shutil
import codecs
import tempfile
import re
import os
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

    def _process_subtitle_line_break(self, subtitle_path: Path, max_chars: int = 25) -> Path:
        """
        处理字幕文件的长行自动换行（核心新增方法）
        :param subtitle_path: 原字幕文件路径
        :param max_chars: 每行最大汉字数，默认25
        :return: 处理后的临时字幕文件路径
        """
        if subtitle_path.suffix.lower() not in ['.srt', '.ass']:
            logger.warning(f"不支持的字幕格式 {subtitle_path.suffix}，跳过自动换行处理")
            return subtitle_path

        # 创建临时文件（后缀与原文件一致，避免FFmpeg解析异常）
        temp_fd, temp_path = tempfile.mkstemp(
            suffix=subtitle_path.suffix,
            prefix="subtitle_processed_",
            dir=subtitle_path.parent
        )
        temp_path = Path(temp_path)
        logger.info(f"处理字幕自动换行，生成临时文件：{temp_path}")

        try:
            content = subtitle_path.read_text(encoding='utf-8')
            processed_content = ""

            if subtitle_path.suffix.lower() == '.srt':
                # SRT格式解析：数字\n时间轴\n字幕内容\n\n
                srt_pattern = re.compile(r'(\d+)\r?\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\r?\n([\s\S]*?)(?=\r?\n\r?\n|$)')
                matches = srt_pattern.findall(content)

                for idx, start_time, end_time, text in matches:
                    clean_text = text.strip()
                    if not clean_text:
                        processed_content += f"{idx}\n{start_time} --> {end_time}\n{text}\n\n"
                        continue

                    # 拆分长行：超过25字自动换行
                    lines = []
                    current_line = ""
                    char_count = 0

                    for char in clean_text:
                        char_count += 1  # 所有字符统一计数（可根据需求调整：中文字符+1，英文+0.5）
                        current_line += char

                        if char_count >= max_chars:
                            lines.append(current_line)
                            current_line = ""
                            char_count = 0

                    if current_line:
                        lines.append(current_line)

                    processed_text = "\n".join(lines)
                    processed_content += f"{idx}\n{start_time} --> {end_time}\n{processed_text}\n\n"

            elif subtitle_path.suffix.lower() == '.ass':
                # ASS格式解析：重点处理Dialogue行的文本
                ass_lines = content.splitlines()
                for line in ass_lines:
                    if line.startswith('Dialogue:'):
                        # ASS Dialogue格式：Dialogue: Marked,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
                        parts = line.split(',', 9)  # 前9个字段分割，最后一个是字幕文本
                        if len(parts) < 10:
                            processed_content += line + "\n"
                            continue

                        dialogue_prefix = ','.join(parts[:9])
                        text = parts[9].strip().replace('\\N', '')  # 移除原有换行

                        if not text:
                            processed_content += line + "\n"
                            continue

                        # 拆分长行（ASS用\N表示换行）
                        lines = []
                        current_line = ""
                        char_count = 0

                        for char in text:
                            char_count += 1
                            current_line += char

                            if char_count >= max_chars:
                                lines.append(current_line)
                                current_line = ""
                                char_count = 0

                        if current_line:
                            lines.append(current_line)

                        processed_text = "\\N".join(lines)
                        processed_content += f"{dialogue_prefix},{processed_text}\n"
                    else:
                        # 非Dialogue行直接保留（样式/脚本等）
                        processed_content += line + "\n"

            # 写入处理后的临时文件
            temp_path.write_text(processed_content, encoding='utf-8')
            return temp_path

        except Exception as e:
            logger.error(f"处理字幕自动换行失败：{e}", exc_info=True)
            temp_path.unlink(missing_ok=True)  # 失败则删除临时文件
            return subtitle_path
        finally:
            os.close(temp_fd)  # 关闭临时文件描述符

    def burn_subtitles(self, video_path: str, subtitle_path: str,
                       output_path: str,
                       style: Optional[dict] = None) -> str:
        """
        将字幕烧录到视频中（修复音频丢失+字幕缺失问题 + 新增25字自动换行）
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

        # 临时文件标记（用于后续清理）
        processed_subtitle_path = None
        need_clean_temp = False

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

            # === 核心新增：处理字幕长行自动换行（超过25字） ===
            processed_subtitle_path = self._process_subtitle_line_break(subtitle_path, max_chars=25)
            need_clean_temp = processed_subtitle_path != subtitle_path

            # 2. 构建FFmpeg命令（使用处理后的临时字幕文件）
            input_stream = ffmpeg.input(str(video_path))
            subtitle_input = ffmpeg.input(str(processed_subtitle_path))  # 加载处理后的字幕

            # 应用字幕滤镜
            if processed_subtitle_path.suffix.lower() == '.ass':
                # ASS字幕：指定字体路径，修复字体缺失导致的字幕不显示
                ass_filter_kwargs = {'filename': str(processed_subtitle_path)}
                if self.font_path:
                    ass_filter_kwargs['fontsdir'] = str(Path(self.font_path).parent)  # 字体目录
                video = ffmpeg.filter(input_stream['v'], 'ass', **ass_filter_kwargs)
            else:
                # SRT字幕：修复force_style传递方式，增加编码指定
                sub_filter_kwargs = {
                    'filename': str(processed_subtitle_path),
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
        finally:
            # === 清理临时字幕文件 ===
            if need_clean_temp and processed_subtitle_path and processed_subtitle_path.exists():
                try:
                    processed_subtitle_path.unlink()
                    logger.info(f"清理临时字幕文件：{processed_subtitle_path}")
                except Exception as e:
                    logger.warning(f"清理临时字幕文件失败：{e}")

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







