# core/translator.py
import json
import asyncio
import time
import requests
import ssl
import urllib3
from typing import List, Dict, Optional
from config.settings import config
from utils.logger import setup_logger

# ==================== 简化版全局SSL禁用（避免SSLContext调用冲突） ====================
# 1. 禁用所有SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
# 2. 全局禁用SSL证书验证（仅保留这一行，移除复杂的HTTPSHandler，避免冲突）
ssl._create_default_https_context = ssl._create_unverified_context

logger = setup_logger(__name__)

class LLMTranslator:
    """Ollama专用翻译器（修复SSLContext不可调用 + 全HTTP）"""
    def __init__(self):
        # 1. 优先初始化provider并强制锁定local模式
        self.provider = config.TRANSLATION_PROVIDER
        if self.provider != "local":
            logger.warning(f"强制切换到local模式（避免SSL错误），原配置: {self.provider}")
            self.provider = "local"
        # 2. 初始化其他属性
        self.api_key = self._get_api_key()
        self.base_url = self._get_base_url()  # 强制HTTP地址
        self.session = None  # 仅用requests.Session，不用openai/anthropic客户端
        self._init_client()

    def _get_api_key(self) -> str:
        """仅返回Ollama的占位Key（无需真实值）"""
        return getattr(config, "LOCAL_API_KEY", "ollama-no-key") or "ollama-no-key"

    def _get_base_url(self) -> str:
        """硬编码Ollama HTTP地址，彻底杜绝HTTPS"""
        ollama_url = "http://localhost:11434/v1"
        logger.info(f"强制使用Ollama HTTP地址: {ollama_url}")
        return ollama_url

    def _init_client(self):
        """仅初始化纯HTTP的requests.Session（无任何SSL相关冲突代码）"""
        self.session = requests.Session()
        # 仅保留必要的Header，无SSL配置（避免触发SSLContext）
        self.session.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        logger.info("Ollama客户端初始化完成（无SSL冲突，纯HTTP）")

    async def translate_single(self, segment: Dict) -> Dict:
        """翻译单条字幕（仅Ollama，无SSL调用）"""
        prompt = self._build_prompt(segment["text"])
        
        try:
            # Ollama OpenAI兼容API请求（纯HTTP，无SSL验证）
            payload = {
                "model": getattr(config, "LOCAL_MODEL", "gemma3:27b"),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 500
            }
            # 仅用HTTP，无需verify参数（避免触发SSLContext）
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.session.post(
                    f"{self.base_url}/chat/completions",
                    json=payload,
                    timeout=120  # gemma3:27b响应慢，超时120秒
                )
            )
            if response.status_code != 200:
                raise Exception(f"Ollama API错误: {response.status_code} - {response.text}")
            
            result = response.json()
            translation = result["choices"][0]["message"]["content"].strip()

            return {
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"],
                "translation": translation
            }

        except Exception as e:
            logger.error(f"翻译失败: {e}，原文: {segment['text']}")
            # 降级返回原文
            return {
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"],
                "translation": segment["text"]
            }

    async def translate_batch(self, segments: List[Dict], batch_size: int = 3) -> List[Dict]:
        """批量翻译（减小批次，适配gemma3:27b）"""
        translated_segments = []
        total = len(segments)
        logger.info(f"批量翻译（Ollama gemma3:27b），共{total}条，批次{batch_size}")

        for i in range(0, total, batch_size):
            batch = segments[i:i+batch_size]
            logger.info(f"处理批次 {i//batch_size + 1}/{(total + batch_size -1)//batch_size}")
            
            tasks = [self.translate_single(seg) for seg in batch]
            batch_results = await asyncio.gather(*tasks)
            translated_segments.extend(batch_results)
            
            # 给Ollama留足响应时间，避免过载
            await asyncio.sleep(1)

        logger.info(f"批量翻译完成：{len(translated_segments)}条")
        return translated_segments

    def _build_prompt(self, text: str) -> str:
        """精简提示词，提升gemma3:27b响应速度"""
        prompt = f"""请将以下日语文本翻译成简体中文，要求准确、自然、口语化，仅返回译文：
{text}"""
        return prompt.strip()

    def translate_sync(self, text: str) -> str:
        """同步翻译（备用接口）"""
        prompt = self._build_prompt(text)
        
        try:
            payload = {
                "model": getattr(config, "LOCAL_MODEL", "gemma3:27b"),
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 1000
            }
            response = self.session.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                timeout=120
            )
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"].strip()
            else:
                raise Exception(f"Ollama错误: {response.status_code}")
        except Exception as e:
            logger.error(f"同步翻译失败: {e}")
            return text

# 测试代码（无SSL冲突）
if __name__ == "__main__":
    # 强制配置
    config.TRANSLATION_PROVIDER = "local"
    config.LOCAL_MODEL = "gemma3:27b"

    # 实例化并测试
    translator = LLMTranslator()
    test_seg = {"start": 0.0, "end": 5.0, "text": "こんにちは、世界！今日は天気がいいですね。"}
    res = asyncio.run(translator.translate_single(test_seg))
    print(f"原文: {res['text']}")
    print(f"译文: {res['translation']}")





