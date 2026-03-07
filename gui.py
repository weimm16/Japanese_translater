# 添加一个简单的GUI版本 (gui.py)
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import asyncio
import threading
import os
import shutil
from pathlib import Path
from main import VideoTranslator, TOTAL_STEPS
from config.settings import config
# 导入配置保存/读取工具
from utils.config_saver import save_gui_config, load_gui_config

class TranslatorGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("日语视频翻译器")
        self.root.geometry("700x500")  # 放大窗口，适配新控件
        self.root.resizable(False, False)  # 固定窗口大小

        self.translator = None
        # 加载持久化配置
        self.gui_config = load_gui_config()
        # 初始化控件变量
        self.init_vars()
        # 搭建UI
        self.setup_ui()

    def init_vars(self):
        """初始化控件变量"""
        # 模型选择（加载配置）
        self.model_var = tk.StringVar(value=self.gui_config["model"])
        # API选择（加载配置）
        self.api_var = tk.StringVar(value=self.gui_config["api"])
        # 语言选择（加载配置）
        self.language_var = tk.StringVar(value=self.gui_config.get("language", "ja - 日语"))
        # 是否烧录字幕（新增，加载配置）
        self.burn_var = tk.BooleanVar(value=self.gui_config["burn_subtitles"])
        # 视频路径/输出路径
        self.video_path = tk.StringVar(value="")
        self.output_path = tk.StringVar(value="")

    def setup_ui(self):
        # ========== 1. 视频文件选择 ==========
        tk.Label(self.root, text="源视频文件:").pack(pady=(10, 5), anchor=tk.W, padx=20)
        self.file_frame = tk.Frame(self.root)
        self.file_frame.pack(fill=tk.X, padx=20)
        tk.Entry(self.file_frame, textvariable=self.video_path, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(self.file_frame, text="浏览", command=self.browse_video).pack(side=tk.RIGHT, padx=5)

        # ========== 2. 输出路径选择（新增） ==========
        tk.Label(self.root, text="输出保存路径:").pack(pady=5, anchor=tk.W, padx=20)
        self.output_frame = tk.Frame(self.root)
        self.output_frame.pack(fill=tk.X, padx=20)
        tk.Entry(self.output_frame, textvariable=self.output_path, width=50).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(self.output_frame, text="选择", command=self.browse_output).pack(side=tk.RIGHT, padx=5)

        # ========== 3. 配置选项（新增仅生成字幕复选框） ==========
        self.options_frame = tk.LabelFrame(self.root, text="配置", padx=10, pady=10)
        self.options_frame.pack(fill=tk.X, padx=20, pady=10)

        # 第一行配置
        # 模型选择
        tk.Label(self.options_frame, text="Whisper模型:").grid(row=0, column=0, sticky=tk.W, pady=5)
        model_combo = ttk.Combobox(self.options_frame, textvariable=self.model_var,
                                   values=["tiny", "base", "small", "medium", "large-v3", "kotoba-whisper"], state="readonly")
        model_combo.grid(row=0, column=1, sticky=tk.W, padx=10)

        # API选择
        tk.Label(self.options_frame, text="翻译API:").grid(row=0, column=2, sticky=tk.W, pady=5)
        api_combo = ttk.Combobox(self.options_frame, textvariable=self.api_var,
                                values=["openai", "anthropic", "local"], state="readonly")
        api_combo.grid(row=0, column=3, sticky=tk.W, padx=10)

        # 仅生成字幕（不烧录）复选框（新增）
        tk.Checkbutton(self.options_frame, text="生成烧录后的视频",
                       variable=self.burn_var, command=self.on_burn_checked).grid(row=0, column=4, sticky=tk.W, padx=10)
        
        # 第二行配置
        # 语言选择
        tk.Label(self.options_frame, text="源语言:").grid(row=1, column=0, sticky=tk.W, pady=5)
        language_values = [f"{code} - {name}" for code, name in config.SUPPORTED_LANGUAGES.items()]
        language_combo = ttk.Combobox(self.options_frame, textvariable=self.language_var,
                                      values=language_values, state="readonly")
        language_combo.grid(row=1, column=1, sticky=tk.W, padx=10)

        # ========== 4. 进度条 + 状态 ==========
        self.progress = ttk.Progressbar(self.root, length=600, mode='determinate')
        self.progress.pack(pady=10)
        self.status_label = tk.Label(self.root, text="就绪", fg="#666666")
        self.status_label.pack()

        # ========== 5. 功能按钮（新增打开目录） ==========
        self.btn_frame = tk.Frame(self.root)
        self.btn_frame.pack(pady=20)
        # 开始翻译
        self.start_btn = tk.Button(self.btn_frame, text="开始翻译", command=self.start_translation,
                                   bg="#4CAF50", fg="white", font=("Arial", 12), width=15)
        self.start_btn.grid(row=0, column=0, padx=10)
        # 打开保存目录（新增）
        self.open_dir_btn = tk.Button(self.btn_frame, text="打开保存目录", command=self.open_output_dir,
                                      bg="#2196F3", fg="white", font=("Arial", 12), width=15)
        self.open_dir_btn.grid(row=0, column=1, padx=10)

    def browse_video(self):
        """浏览选择源视频"""
        filename = filedialog.askopenfilename(
            filetypes=[("Video files", "*.mp4 *.mkv *.avi *.mov"), ("All files", "*.*")]
        )
        if filename:
            self.video_path.set(filename)
            # 自动填充输出路径（源视频同目录+_translated.mp4）
            if not self.output_path.get():
                video_p = Path(filename)
                output_name = f"{video_p.stem}_translated.mp4"
                self.output_path.set(str(video_p.parent / output_name))

    def browse_output(self):
        """浏览选择输出文件（自定义保存路径/文件名）"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".mp4",
            filetypes=[("MP4视频", "*.mp4"), ("所有文件", "*.*")]
        )
        if filename:
            self.output_path.set(filename)

    def on_burn_checked(self):
        """勾选仅生成字幕后的提示"""
        if not self.burn_var.get():
            self.status_label.config(text="提示：仅生成SRT/ASS字幕文件，不输出视频", fg="#FF9800")
        else:
            self.status_label.config(text="就绪", fg="#666666")

    def open_output_dir(self):
        """打开保存目录"""
        output_p = Path(self.output_path.get()) if self.output_path.get() else Path(config.OUTPUT_DIR)
        if output_p.parent.exists():
            # 跨平台打开目录
            if os.name == "nt":  # Windows
                os.startfile(output_p.parent)
            else:  # Mac/Linux
                os.system(f"open {output_p.parent}" if os.uname().sysname == "Darwin" else f"xdg-open {output_p.parent}")
        else:
            messagebox.showwarning("警告", "保存目录不存在！")

    def start_translation(self):
        """开始翻译（校验+启动后台线程）"""
        # 1. 校验输入
        video_path = self.video_path.get()
        output_path = self.output_path.get()
        if not video_path:
            messagebox.showerror("错误", "请选择源视频文件！")
            return
        if not output_path:
            messagebox.showerror("错误", "请选择输出保存路径！")
            return
        
        # 新增：API密钥校验
        api_provider = self.api_var.get()
        if api_provider == "openai" and not config.OPENAI_API_KEY:
            messagebox.showerror("错误", "未配置OpenAI API密钥！请检查.env文件或系统环境变量")
            return
        if api_provider == "anthropic" and not config.ANTHROPIC_API_KEY:
            messagebox.showerror("错误", "未配置Anthropic API密钥！请检查.env文件或系统环境变量")
            return
        
        # 2. 更新全局配置
        config.WHISPER_MODEL = self.model_var.get()
        config.TRANSLATION_PROVIDER = self.api_var.get()
        # 提取语言代码（从"ja - 日语"格式中提取"ja"）
        language_full = self.language_var.get()
        language_code = language_full.split(" - ")[0] if " - " in language_full else language_full
        config.WHISPER_LANGUAGE = language_code
        # 3. 保存GUI配置（持久化）
        save_gui_config({
            "model": self.model_var.get(),
            "api": self.api_var.get(),
            "language": language_full,
            "burn_subtitles": self.burn_var.get()
        })
        # 4. 禁用按钮+更新状态
        self.start_btn.config(state=tk.DISABLED)
        self.status_label.config(text="处理中...【提取音频】", fg="#4CAF50")
        self.progress.config(value=0)
        # 5. 后台线程运行（避免GUI卡死）
        thread = threading.Thread(target=self.run_async_task, args=(video_path, output_path))
        thread.daemon = True  # 守护线程，关闭GUI时自动退出
        thread.start()

    def run_async_task(self, video_path, output_path):
        """运行异步任务（优化事件循环创建）"""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(self.process_video(video_path, output_path))

    def update_progress(self, step, total):
        """进度更新回调（UI安全更新）"""
        progress_val = (step / total) * 100
        step_desc = {
            1: "提取音频",
            2: "语音识别",
            3: "翻译文本",
            4: "烧录字幕"
        }
        
        # 处理模型下载的进度更新
        if step < 2 and progress_val < 10:
            status_text = "处理中...【下载模型】"
        else:
            status_text = f"处理中...【{step_desc.get(step, '完成')}】"
            
        self.root.after(0, lambda: self.progress.config(value=progress_val))
        self.root.after(0, lambda: self.status_label.config(
            text=status_text,
            fg="#4CAF50"
        ))

    async def process_video(self, video_path, output_path):
        """处理视频核心逻辑"""
        try:
            self.translator = VideoTranslator()
            # 提取语言代码
            language_full = self.language_var.get()
            language_code = language_full.split(" - ")[0] if " - " in language_full else language_full
            
            # 调用process，传入进度回调+自定义输出路径+是否烧录+源语言
            results = await self.translator.process(
                video_path,
                output_name=output_path,
                burn_subtitles=self.burn_var.get(),
                source_language=language_code,
                progress_callback=self.update_progress
            )
            # 处理完成（UI更新）- 优化results作用域
            self.root.after(0, lambda res=results: self.on_complete(res))
        except Exception as e:
            # 修复：通过默认参数捕获当前e的值，解决作用域问题
            self.root.after(0, lambda err=e: self.on_error(str(err)))

    def on_complete(self, results):
        """处理完成回调"""
        self.progress.config(value=100)
        self.status_label.config(text="处理完成！", fg="#4CAF50")
        self.start_btn.config(state=tk.NORMAL)
        # 拼接提示信息
        msg = "翻译完成！\n\n"
        if results.get('translation_path'):
            msg += f"SRT字幕: {results['translation_path']}\n"
            msg += f"ASS字幕: {results['subtitle_path']}\n"
        if results.get('output_path'):
            msg += f"输出视频: {results['output_path']}"
        else:
            msg += "（仅生成字幕，未输出视频）"
        messagebox.showinfo("完成", msg)

    def on_error(self, error_msg):
        """处理错误回调"""
        self.progress.config(value=0)
        self.status_label.config(text="处理失败！", fg="#F44336")
        self.start_btn.config(state=tk.NORMAL)
        messagebox.showerror("错误", f"处理失败：\n{error_msg}")

    def __del__(self):
        """析构函数：清理临时文件"""
        if hasattr(self, 'translator') and self.translator:
            self.translator.cleanup()

    def run(self):
        """启动GUI"""
        self.root.mainloop()

if __name__ == "__main__":
    app = TranslatorGUI()
    app.run()