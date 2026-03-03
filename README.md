# 日语视频翻译器

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Dependencies](https://img.shields.io/badge/dependencies-up%20to%20date-brightgreen)](requirements.txt)

一款本地化部署的日语视频翻译工具，支持音频提取、语音识别、智能翻译、字幕生成与视频烧录全流程，无需依赖第三方付费API（可本地化部署Qwen2.5模型）。

## 🌟 核心功能
- 🎵 **音频提取**：自动从视频中提取音频（支持MP4/MKV/AVI/MOV等格式）
- 🗣️ **语音识别**：基于OpenAI Whisper识别日语语音，生成精准时间戳字幕
- 📝 **智能翻译**：支持Qwen2.5（本地）/OpenAI/Anthropic多引擎翻译日语到中文
- 🎬 **字幕生成**：生成标准SRT/ASS字幕文件，支持自定义字体/样式
- 🎥 **字幕烧录**：将翻译后的字幕无缝烧录到视频中，输出完整翻译视频

## 📋 环境准备

### 系统要求
| 系统       | 最低配置                          | 推荐配置                          |
|------------|-----------------------------------|-----------------------------------|
| Windows    | Python 3.8+, 8GB内存, 空闲空间20GB | Python 3.10+, 16GB内存, GPU（4GB+） |
| macOS      | Python 3.8+, 8GB内存, 空闲空间20GB | Python 3.10+, 16GB内存, M1/M2芯片  |
| Linux      | Python 3.8+, 8GB内存, 空闲空间20GB | Python 3.10+, 16GB内存, GPU（4GB+） |

### 必装依赖
1. **Python 3.8+**：[官网下载](https://www.python.org/downloads/)
2. **FFmpeg**：用于音频提取和视频处理
   - Windows：下载[FFmpeg](https://ffmpeg.org/download.html)并添加到系统PATH
   - macOS：`brew install ffmpeg`
   - Linux：`sudo apt install ffmpeg`
3. **Ollama（可选）**：本地化部署Qwen2.5模型时需安装
   - 下载地址：[Ollama官网](https://ollama.com/)

## 🚀 安装步骤

### 1. 克隆仓库
```bash
git clone https://github.com/your-username/japanese-video-translator.git
cd japanese-video-translator

# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 安装依赖（包含python-dotenv，确保.env加载）
pip install -r requirements.txt
```
### 2. 安装 Ollama（本地化翻译必备）

    从Ollama 官网下载并安装对应系统版本
    拉取 Qwen2.5 模型（推荐 14B 量化版）：

```bash


ollama pull qwen2.5:14b-int4
```
### 📖 使用指南
方式 1：图形界面（GUI，推荐新手）
```bash

# 激活虚拟环境后执行
python gui.py
```
```bash
GUI 操作流程

    选择源视频：点击「浏览」选择需要翻译的日语视频文件
    配置参数：
        Whisper 模型：读取.env 的WHISPER_MODEL，可在 GUI 中覆盖
        翻译 API：读取.env 的TRANSLATION_PROVIDER，可在 GUI 中切换
        可选：勾选「仅生成字幕文件」（不烧录到视频）
    选择输出路径：指定翻译后视频 / 字幕的保存位置（默认读取.env 的OUTPUT_DIR）
    开始翻译：点击「开始翻译」，等待处理完成
    查看结果：处理完成后可点击「打开保存目录」查看生成的字幕 / 视频
```
## 方式 2：命令行（CLI，适合开发者 / 批量处理）
```bash

# 基础用法（优先读取.env配置，参数可覆盖.env）
python main.py --video path/to/your/video.mp4 --output path/to/output.mp4

# 仅生成字幕（不烧录视频）
python main.py --video path/to/video.mp4 --skip-burn --output path/to/subtitle.srt

# 覆盖.env的Whisper模型和翻译引擎
python main.py --video path/to/video.mp4 --model medium --provider openai
```
贡献指南

    Fork 本仓库
    创建特性分支：git checkout -b feature/your-feature
    提交修改：git commit -m 'Add some feature'
    推送分支：git push origin feature/your-feature
    提交 Pull Request

🙏 致谢

    OpenAI Whisper：语音识别核心
    Ollama：本地化大模型部署
    FFmpeg：音视频处理
