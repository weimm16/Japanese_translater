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


