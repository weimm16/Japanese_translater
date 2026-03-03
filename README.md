日语视频全自动字幕翻译工具 🎬
一款基于 OpenAI Whisper 实现日语语音精准转录、结合本地 / 云端 LLM 完成日译中，且支持字幕生成与硬字幕烧录的跨平台工具，完美解决日语视频字幕超长、缺失、格式不兼容等问题，无需专业操作，一键完成视频字幕全流程处理。
✨ 核心特性

    ✅ 跨平台支持：Windows/macOS/Linux 全系统适配
    ✅ 智能转录拆分：自动将 30s 超长字幕按 5-10 秒 / 自然标点拆分为短字幕，适配视频显示
    ✅ 多端翻译可选：支持本地 Ollama（Gemma3）/ 云端 OpenAI/Anthropic 翻译，无网络也能跑
    ✅ 双格式字幕生成：自动输出 SRT/ASS 标准字幕文件，支持自定义字体、大小、描边
    ✅ 硬字幕烧录：基于 FFmpeg 将字幕无缝烧录到视频，保留原始音视频质量，无音频丢失
    ✅ 可视化 GUI：图形化操作界面，支持文件选择、配置保存、进度查看、目录快速打开
    ✅ 配置持久化：自动保存模型 / API / 字幕配置，无需重复设置
    ✅ 轻量高效：虚拟环境隔离依赖，临时文件自动清理，无磁盘残留

🛠️ 技术栈

    核心框架：Python 3.8+
    语音转录：OpenAI Whisper
    翻译引擎：Ollama / OpenAI / Anthropic
    音视频处理：FFmpeg
    GUI 界面：Tkinter

📋 环境要求
表格
依赖	最低版本	说明
Python	3.8	推荐 3.9/3.10（兼容性佳）
FFmpeg	5.0	音视频处理核心
内存	8GB	推荐 16GB（加速 Whisper）
GPU（可选）	CUDA 11+	支持 GPU 加速转录（需安装对应 PyTorch）
🚀 安装步骤
1. 克隆仓库

    git clone https://github.com/weimm16/Japanese_translater.git

    cd Japanese_translater

3. 创建并激活虚拟环境
Windows
powershell

# 创建虚拟环境
    python -m venv venv

# 激活虚拟环境
# CMD
    venv\Scripts\activate.bat
# PowerShell
    .\venv\Scripts\Activate.ps1

macOS/Linux

# 创建虚拟环境
    python3 -m venv venv

# 激活虚拟环境
    source venv/bin/activate

3. 安装 Python 依赖

# 升级 pip
    python -m pip install --upgrade pip

# 安装项目依赖
    pip install -r requirements.txt

# 安装 Whisper
    pip install openai-whisper

4. 安装 FFmpeg
Windows

    下载静态包：https://www.gyan.dev/ffmpeg/builds/
    解压到无中文 / 空格路径（如 D:\ffmpeg）
    将 D:\ffmpeg\bin 添加到系统环境变量 Path
    验证：ffmpeg -version

macOS

    brew install ffmpeg

Linux (Ubuntu)

    sudo apt update && sudo apt install ffmpeg -y

🎯 快速开始
1. 配置调整（可选）
修改 config/settings.py 调整核心参数：


# 字幕配置
    SUBTITLE_FONT = "微软雅黑"  # Windows：微软雅黑；macOS：PingFang SC；Linux：WenQuanYi ZenHei
    SUBTITLE_FONT_SIZE = 24     # 字幕字体大小

2. 运行可视化界面

    python gui.py

3. 命令行快速处理

    python main.py --video_path test_video.mp4 --output_path output_video.mp4


❓ 常见问题排查
1. FFmpeg 未找到

    检查环境变量是否配置正确，重启终端后验证 ffmpeg -version
    Windows 下确保路径无中文 / 空格

2. Whisper 转录慢

    换更小的模型（如 base），或安装 GPU 版 PyTorch 启用 GPU 加速
    检查内存是否充足，推荐 16GB 以上

3. 字幕缺失

    检查音频是否提取完整，或调整 Whisper 提示词 / 参数
    确保字幕文件编码为 UTF-8

4. Git 推送失败（连接超时）

    切换为 SSH 协议：git remote set-url origin git@github.com:weimm16/Japanese_translater.git
    配置代理：git config --global https.proxy http://127.0.0.1:7890

🤝 贡献指南

    Fork 本仓库
    创建特性分支：git checkout -b feature/xxx
    提交代码：git commit -m 'add: xxx 功能'
    推送分支：git push origin feature/xxx
    提交 Pull Request

📄 许可证
本项目基于 MIT 许可证开源，详见 LICENSE 文件。
📞 联系方式
如有问题或建议，欢迎提交 Issue 或联系开发者。
