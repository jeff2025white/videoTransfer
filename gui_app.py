"""
字幕预览工具 - Tkinter GUI
左右布局：左侧视频播放器，右侧操作面板
"""
import tkinter as tk
from tkinter import filedialog, colorchooser, ttk
from PIL import Image, ImageDraw, ImageFont, ImageTk
import cv2
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.srt_parser import parse_srt, parse_srt_bilingual, get_subtitle_at_time


class SubtitlePreviewApp:
    def __init__(self, root):
        self.root = root
        self.root.title("字幕预览工具")
        self.root.geometry("1280x870")
        self.root.minsize(960, 690)

        # 状态变量
        self.video_path = None
        self.original_video_path = None
        self.burned_video_path = None
        self.video_source = tk.StringVar(value="original")
        self.cap = None
        self.fps = 30
        self.total_frames = 0
        self.current_frame_idx = 0
        self.is_playing = False
        self.after_id = None
        self.play_start_time = 0.0
        self.play_start_frame = 0

        self.subtitles = []
        self.bilingual_subtitles = []  # 双语字幕（含 original + translated）
        self.subtitle_text = ""

        # 字幕样式变量
        self.font_size = tk.IntVar(value=32)
        self.font_color = "#FFFF00"  # 默认黄色
        self.y_position = tk.IntVar(value=85)  # 默认85%位置（靠近底部）
        self.font_name = tk.StringVar(value="msyh.ttc")  # 默认微软雅黑
        self.show_original = tk.BooleanVar(value=True)  # 是否显示原文（中文），默认显示
        self.ass_font_scale = 1.28  # ASS 压制字号校准系数
        self.ass_y_offset_scale = 0.35  # ASS 压制Y轴校准系数（按字号下移）

        self._build_ui()

    def _build_ui(self):
        """构建界面"""
        # 主容器 - 左右分栏
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # 左侧：视频播放区
        left_frame = tk.Frame(main_frame, bg="#1a1a1a")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(left_frame, bg="#1a1a1a", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # 进度条
        progress_frame = tk.Frame(left_frame)
        progress_frame.pack(fill=tk.X, padx=5, pady=3)

        self.progress_var = tk.DoubleVar(value=0)
        self.progress_scale = tk.Scale(
            progress_frame, from_=0, to=100, orient=tk.HORIZONTAL,
            variable=self.progress_var, showvalue=False,
            command=self._on_seek
        )
        self.progress_scale.pack(fill=tk.X)

        self.time_label = tk.Label(progress_frame, text="00:00 / 00:00", font=("Arial", 9))
        self.time_label.pack()

        # 右侧：操作面板
        right_frame = tk.Frame(main_frame, width=280, padx=10, pady=10)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)
        right_frame.pack_propagate(False)

        # --- 文件操作 ---
        tk.Label(right_frame, text="文件操作", font=("Microsoft YaHei", 11, "bold")).pack(anchor=tk.W, pady=(0, 5))

        tk.Button(right_frame, text="打开视频文件", command=self._open_video,
                  width=20, height=1).pack(pady=3)

        self.video_name_label = tk.Label(right_frame, text="未选择视频", fg="gray",
                                         wraplength=240, font=("Arial", 9))
        self.video_name_label.pack(pady=2)

        # 目标语言选择
        lang_frame = tk.Frame(right_frame)
        lang_frame.pack(fill=tk.X, pady=3)
        tk.Label(lang_frame, text="目标语言:").pack(side=tk.LEFT)
        self.target_lang = tk.StringVar(value="英语")
        lang_options = [
            "英语", "简体中文", "繁体中文", "日语", "韩语",
            "法语", "德语", "西班牙语", "俄语", "葡萄牙语",
            "意大利语", "阿拉伯语", "印地语", "泰语", "越南语"
        ]
        lang_combo = ttk.Combobox(lang_frame, textvariable=self.target_lang,
                                  values=lang_options, width=12, state="readonly")
        lang_combo.pack(side=tk.RIGHT)

        # 语言代码映射
        self.lang_code_map = {
            "英语": "en",
            "简体中文": "zh-cn",
            "繁体中文": "zh-tw",
            "日语": "ja",
            "韩语": "ko",
            "法语": "fr",
            "德语": "de",
            "西班牙语": "es",
            "俄语": "ru",
            "葡萄牙语": "pt",
            "意大利语": "it",
            "阿拉伯语": "ar",
            "印地语": "hi",
            "泰语": "th",
            "越南语": "vi"
        }

        tk.Button(right_frame, text="开始翻译", command=self._start_translate,
                  width=20, height=1, bg="#4CAF50", fg="white").pack(pady=5)

        self.translate_status_label = tk.Label(right_frame, text="", fg="gray",
                                               wraplength=240, font=("Arial", 9))
        self.translate_status_label.pack(pady=2)

        # 分隔线
        ttk.Separator(right_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=5)

        srt_btn_frame = tk.Frame(right_frame)
        srt_btn_frame.pack(fill=tk.X, pady=3)
        tk.Button(srt_btn_frame, text="打开译文字幕文件", command=self._open_subtitle,
                  width=14, height=1).pack(side=tk.LEFT)
        tk.Button(srt_btn_frame, text="重新翻译", command=self._retranslate,
                  width=8, height=1).pack(side=tk.RIGHT)

        self.srt_name_label = tk.Label(right_frame, text="未选择字幕", fg="gray",
                                       wraplength=240, font=("Arial", 9))
        self.srt_name_label.pack(pady=2)

        # 分隔线
        ttk.Separator(right_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # --- 字幕样式 ---
        tk.Label(right_frame, text="字幕样式", font=("Microsoft YaHei", 11, "bold")).pack(anchor=tk.W, pady=(0, 5))

        # 字体选择
        font_frame = tk.Frame(right_frame)
        font_frame.pack(fill=tk.X, pady=3)
        tk.Label(font_frame, text="字体:").pack(side=tk.LEFT)
        font_options = ["msyh.ttc", "simhei.ttf", "simsun.ttc", "arial.ttf"]
        font_combo = ttk.Combobox(font_frame, textvariable=self.font_name,
                                  values=font_options, width=14, state="readonly")
        font_combo.pack(side=tk.RIGHT)

        # 字体大小
        size_frame = tk.Frame(right_frame)
        size_frame.pack(fill=tk.X, pady=3)
        tk.Label(size_frame, text="字体大小:").pack(side=tk.LEFT)
        tk.Scale(size_frame, from_=12, to=72, orient=tk.HORIZONTAL,
                 variable=self.font_size, length=150).pack(side=tk.RIGHT)

        # 字体颜色
        color_frame = tk.Frame(right_frame)
        color_frame.pack(fill=tk.X, pady=3)
        tk.Label(color_frame, text="字体颜色:").pack(side=tk.LEFT)
        self.color_btn = tk.Button(color_frame, text="  ", bg=self.font_color,
                                   width=4, command=self._pick_color)
        self.color_btn.pack(side=tk.RIGHT)

        # Y轴位置
        pos_frame = tk.Frame(right_frame)
        pos_frame.pack(fill=tk.X, pady=3)
        tk.Label(pos_frame, text="Y轴位置:").pack(side=tk.LEFT)
        tk.Label(pos_frame, text="(顶 0% ← → 100% 底)", font=("Arial", 8), fg="gray").pack(side=tk.LEFT, padx=5)

        self.y_scale = tk.Scale(right_frame, from_=0, to=100, orient=tk.HORIZONTAL,
                                variable=self.y_position, length=240)
        self.y_scale.pack(pady=3)

        # 显示原文选项
        tk.Checkbutton(right_frame, text="显示原文（中文）",
                       variable=self.show_original).pack(anchor=tk.W, pady=3)

        # 应用按钮：将当前样式设置刷新到视频预览
        tk.Button(right_frame, text="应用", command=self._apply_style,
                  width=20, height=1).pack(pady=5)

        # 字幕压制按钮
        tk.Button(right_frame, text="字幕压制", command=self._burn_subtitle,
                  width=20, height=1, bg="#FF5722", fg="white").pack(pady=8)
        self.burn_status_label = tk.Label(right_frame, text="", fg="gray",
                                          wraplength=240, font=("Arial", 9))
        self.burn_status_label.pack(pady=2)

        # 分隔线
        ttk.Separator(right_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)

        # --- 播放控制 ---
        tk.Label(right_frame, text="播放控制", font=("Microsoft YaHei", 11, "bold")).pack(anchor=tk.W, pady=(0, 5))

        source_frame = tk.Frame(right_frame)
        source_frame.pack(anchor=tk.W, pady=3)
        tk.Label(source_frame, text="视频源:").pack(side=tk.LEFT)
        tk.Radiobutton(source_frame, text="原视频", variable=self.video_source,
                       value="original", command=self._on_video_source_change).pack(side=tk.LEFT)
        tk.Radiobutton(source_frame, text="新视频", variable=self.video_source,
                       value="burned", command=self._on_video_source_change).pack(side=tk.LEFT)

        ctrl_frame = tk.Frame(right_frame)
        ctrl_frame.pack(pady=5)

        self.play_btn = tk.Button(ctrl_frame, text="▶ 播放", command=self._toggle_play,
                                  width=10, height=1)
        self.play_btn.pack(side=tk.LEFT, padx=5)

        tk.Button(ctrl_frame, text="⏹ 停止", command=self._stop,
                  width=10, height=1).pack(side=tk.LEFT, padx=5)
        tk.Button(ctrl_frame, text="📂", command=self._open_burned_video_folder,
                  width=4, height=1).pack(side=tk.LEFT, padx=5)

    def _open_video(self):
        """打开视频文件"""
        path = filedialog.askopenfilename(
            title="选择视频文件",
            filetypes=[("视频文件", "*.mp4 *.mkv *.avi *.mov *.flv"), ("所有文件", "*.*")]
        )
        if not path:
            return

        self.video_path = path
        self.original_video_path = path
        self.burned_video_path = None
        self.video_source.set("original")
        self.video_name_label.config(text=os.path.basename(path), fg="black")

        # 释放之前的视频
        if self.cap:
            self.cap.release()

        self.cap = cv2.VideoCapture(path)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.current_frame_idx = 0
        self.is_playing = False
        self.play_btn.config(text="▶ 播放")

        # 更新进度条范围
        self.progress_scale.config(to=self.total_frames)
        self.progress_var.set(0)

        # 显示第一帧
        self._show_frame()

    def _open_subtitle(self):
        """打开字幕文件：选择并用记事本打开，同时加载到播放器"""
        path = filedialog.askopenfilename(
            title="选择字幕文件",
            filetypes=[("SRT字幕", "*.srt"), ("所有文件", "*.*")]
        )
        if not path:
            return

        self._load_srt(path)
        self.srt_name_label.config(text=os.path.basename(path), fg="black")

        # 用记事本打开字幕文件
        import subprocess
        subprocess.Popen(["notepad.exe", path])

        # 如果当前有帧在显示，刷新一下以显示字幕
        if self.cap and not self.is_playing:
            self._show_frame()

    def _start_translate(self):
        """开始翻译：调用 subtitle_translator 进行 ASR + 大模型翻译"""
        if not self.video_path:
            self.translate_status_label.config(text="请先打开视频文件", fg="red")
            return

        lang_name = self.target_lang.get()
        lang_code = self.lang_code_map.get(lang_name, "en")

        self.translate_status_label.config(text=f"正在翻译为{lang_name}...", fg="blue")
        self.root.update()

        # 在子线程中执行翻译，避免阻塞 UI
        import threading
        thread = threading.Thread(target=self._do_translate, args=(lang_code,), daemon=True)
        thread.start()

    def _do_translate(self, lang_code: str):
        """在子线程中执行翻译"""
        import subprocess

        script_dir = os.path.dirname(os.path.abspath(__file__))
        python_exe = os.path.join(script_dir, "venv2", "Scripts", "python.exe")
        translator_script = os.path.join(script_dir, "subtitle_translator.py")

        source_video_path = self.original_video_path or self.video_path
        cmd = [python_exe, translator_script, "-i", source_video_path, "-t", lang_code]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=script_dir)
            if result.returncode == 0:
                # 翻译成功，找到生成的 SRT 文件
                base_name = os.path.splitext(source_video_path)[0]
                srt_path = f"{base_name}.srt"
                if os.path.exists(srt_path):
                    self._load_srt(srt_path)
                    self.root.after(0, lambda: self.srt_name_label.config(
                        text=os.path.basename(srt_path), fg="black"))
                    self.root.after(0, lambda: self.translate_status_label.config(
                        text="翻译完成，请审核字幕后再压制", fg="green"))
                    # 用记事本打开字幕文件供用户审核
                    subprocess.Popen(["notepad.exe", srt_path])
                    # 刷新当前帧显示字幕预览
                    if self.cap and not self.is_playing:
                        self.root.after(0, self._show_frame)
                else:
                    self.root.after(0, lambda: self.translate_status_label.config(
                        text="翻译完成，但未找到输出文件", fg="orange"))
            else:
                err_msg = result.stderr[:100] if result.stderr else "未知错误"
                self.root.after(0, lambda: self.translate_status_label.config(
                    text=f"翻译失败: {err_msg}", fg="red"))
        except Exception as e:
            self.root.after(0, lambda: self.translate_status_label.config(
                text=f"执行异常: {str(e)[:80]}", fg="red"))

    def _retranslate(self):
        """重新翻译：从磁盘重新读取SRT文件中的中文原文，翻译为目标语言（不做语音识别）"""
        # 先从磁盘重新加载字幕文件（用户可能在记事本中修改了）
        if self.video_path:
            base_name = os.path.splitext(self.original_video_path or self.video_path)[0]
            srt_path = f"{base_name}.srt"
            if os.path.exists(srt_path):
                self._load_srt(srt_path)
            else:
                self.translate_status_label.config(text="未找到字幕文件，请先翻译", fg="red")
                return

        if not self.subtitles:
            self.translate_status_label.config(text="请先加载字幕文件", fg="red")
            return

        lang_name = self.target_lang.get()
        lang_code = self.lang_code_map.get(lang_name, "en")

        self.translate_status_label.config(text=f"正在重新翻译为{lang_name}...", fg="blue")
        self.root.update()

        import threading
        thread = threading.Thread(target=self._do_retranslate, args=(lang_code,), daemon=True)
        thread.start()

    def _do_retranslate(self, lang_code: str):
        """在子线程中执行重新翻译"""
        try:
            from core.translator import translate_segments
            import config

            # 从当前字幕构造 segments 格式：只使用中文原文，不把旧译文再次送去翻译
            segments = []
            if self.bilingual_subtitles:
                for sub in self.bilingual_subtitles:
                    source_text = sub.get("original", "") or sub.get("translated", "")
                    segments.append({
                        "start": sub["start"],
                        "end": sub["end"],
                        "text": source_text
                    })
            else:
                for sub in self.subtitles:
                    segments.append({
                        "start": sub["start"],
                        "end": sub["end"],
                        "text": sub["text"]
                    })

            # 调用大模型翻译
            translated = translate_segments(
                segments=segments,
                target_lang=lang_code,
                source_lang="zh",
                api_key=None
            )

            # 写入 SRT 文件
            if self.video_path:
                base_name = os.path.splitext(self.original_video_path or self.video_path)[0]
                srt_path = f"{base_name}.srt"
            else:
                srt_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "retranslated.srt")

            from core.srt_writer import write_srt
            write_srt(translated, srt_path)

            # 重新加载字幕
            self._load_srt(srt_path)
            self.root.after(0, lambda: self.srt_name_label.config(
                text=os.path.basename(srt_path), fg="black"))
            self.root.after(0, lambda: self.translate_status_label.config(
                text="重新翻译完成，请审核字幕", fg="green"))

            # 用记事本打开供审核
            import subprocess
            subprocess.Popen(["notepad.exe", srt_path])

            # 刷新预览
            if self.cap and not self.is_playing:
                self.root.after(0, self._show_frame)

        except Exception as e:
            self.root.after(0, lambda: self.translate_status_label.config(
                text=f"重新翻译失败: {str(e)[:80]}", fg="red"))

    def _apply_style(self):
        """应用当前字幕样式设置，刷新视频预览"""
        if self.cap and self.subtitles:
            if not self.is_playing:
                self._show_frame()

    def _load_srt(self, srt_path):
        """统一加载 SRT 字幕文件（同时解析双语）"""
        self.subtitles = parse_srt(srt_path)
        self.bilingual_subtitles = parse_srt_bilingual(srt_path)

    def _pick_color(self):
        """选择字幕颜色"""
        color = colorchooser.askcolor(initialcolor=self.font_color, title="选择字幕颜色")
        if color[1]:
            self.font_color = color[1]
            self.color_btn.config(bg=self.font_color)
            # 刷新当前帧
            if self.cap and not self.is_playing:
                self._show_frame()

    def _burn_subtitle(self):
        """字幕压制：将当前字幕用设置的样式烧录到视频"""
        if not self.video_path:
            self.burn_status_label.config(text="请先打开视频文件", fg="red")
            return
        if not self.subtitles:
            self.burn_status_label.config(text="请先加载字幕文件", fg="red")
            return

        self.burn_status_label.config(text="正在压制字幕...", fg="blue")
        self.root.update()

        import threading
        thread = threading.Thread(target=self._do_burn, daemon=True)
        thread.start()

    def _do_burn(self):
        """在子线程中执行字幕压制"""
        try:
            from core.srt_writer import write_ass
            from core.subtitle_detector import detect_subtitle_region
            from core.burner import burn_subtitles

            # 用 GUI 上设置的样式生成 ASS 文件
            source_video_path = self.original_video_path or self.video_path
            base_name = os.path.splitext(source_video_path)[0]
            ass_path = f"{base_name}_gui_burn.ass"
            output_path = f"{base_name}_burned.mp4"

            # 构造 subtitle_info，使用 GUI 设置的参数
            video_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            video_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            font_size = self.font_size.get()
            y_percent = self.y_position.get() / 100.0
            y_center = int(video_height * y_percent)

            subtitle_info = {
                "video_height": video_height,
                "video_width": video_width,
                "font_size": font_size,
                "y_top": y_center - font_size // 2,
                "y_bottom": y_center + font_size // 2,
                "detected": True
            }

            # 构造 translated_segments 格式：默认仅使用译文，原文按选项单独处理
            translated_segments = []
            source_subtitles = self.bilingual_subtitles if self.bilingual_subtitles else []
            if source_subtitles:
                for sub in source_subtitles:
                    translated_segments.append({
                        "start": sub["start"],
                        "end": sub["end"],
                        "original": sub.get("original", ""),
                        "translated": sub.get("translated") or sub.get("original", "")
                    })
            else:
                for sub in self.subtitles:
                    translated_segments.append({
                        "start": sub["start"],
                        "end": sub["end"],
                        "original": "",
                        "translated": sub["text"]
                    })

            # 生成自定义样式的 ASS
            self._write_custom_ass(translated_segments, ass_path, subtitle_info)

            # 调用 ffmpeg 烧录
            burn_subtitles(source_video_path, ass_path, output_path)

            # 压制完成，切换视频源
            if os.path.exists(output_path):
                self.root.after(0, lambda: self._switch_video_source(output_path))
                self.root.after(0, lambda: self.burn_status_label.config(
                    text="压制完成，已切换到新视频", fg="green"))
            else:
                self.root.after(0, lambda: self.burn_status_label.config(
                    text="压制失败：输出文件不存在", fg="red"))

            # 清理临时 ASS 文件
            if os.path.exists(ass_path):
                os.remove(ass_path)

        except Exception as e:
            self.root.after(0, lambda: self.burn_status_label.config(
                text=f"压制失败: {str(e)[:80]}", fg="red"))

    def _write_custom_ass(self, segments, output_path, subtitle_info):
        """根据 GUI 设置生成自定义样式的 ASS 字幕文件"""
        video_height = subtitle_info["video_height"]
        video_width = subtitle_info["video_width"]
        font_size = subtitle_info["font_size"]
        # PIL 预览字号与 ASS/libass 字号不是 1:1，压制侧做视觉校准
        ass_font_size = max(1, int(font_size * self.ass_font_scale))

        # ASS 使用与预览一致的字幕块中心点定位，并补偿 libass 多行文本视觉偏上问题
        y_center = int((subtitle_info["y_top"] + subtitle_info["y_bottom"]) / 2)
        y_center = min(video_height - 5, y_center + int(font_size * self.ass_y_offset_scale))
        x_center = int(video_width / 2)

        # 将颜色从 #RRGGBB 转为 ASS 格式 &H00BBGGRR
        hex_color = self.font_color.lstrip("#")
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        ass_color = f"&H00{b:02X}{g:02X}{r:02X}"

        # 获取字体名（去掉扩展名）
        font_file = self.font_name.get()
        font_name_map = {
            "msyh.ttc": "Microsoft YaHei",
            "simhei.ttf": "SimHei",
            "simsun.ttc": "SimSun",
            "arial.ttf": "Arial"
        }
        ass_font = font_name_map.get(font_file, "Microsoft YaHei")

        with open(output_path, "w", encoding="utf-8") as f:
            f.write("[Script Info]\n")
            f.write("ScriptType: v4.00+\n")
            f.write(f"PlayResX: {video_width}\n")
            f.write(f"PlayResY: {video_height}\n")
            f.write("ScaledBorderAndShadow: yes\n")
            f.write("WrapStyle: 2\n\n")

            f.write("[V4+ Styles]\n")
            f.write("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
                    "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
                    "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
                    "Alignment, MarginL, MarginR, MarginV, Encoding\n")
            f.write(f"Style: Default,{ass_font},{ass_font_size},"
                    f"{ass_color},&H000000FF,&H66505050,&H80000000,"
                    f"0,0,0,0,100,100,0,0,3,8,0,8,20,20,0,1\n\n")

            f.write("[Events]\n")
            f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")

            # 使用预览字号测量文本框，保证换行和文本框尺寸尽量与预览一致
            measure_img = Image.new("RGB", (video_width, video_height))
            measure_draw = ImageDraw.Draw(measure_img)
            try:
                measure_font = ImageFont.truetype(self.font_name.get(), font_size)
            except (OSError, IOError):
                try:
                    measure_font = ImageFont.truetype("msyh.ttc", font_size)
                except (OSError, IOError):
                    measure_font = ImageFont.load_default()
            max_text_w = int(video_width * 0.9)

            for seg in segments:
                start_ts = self._fmt_ass_time(seg["start"])
                end_ts = self._fmt_ass_time(seg["end"])
                text = seg["translated"]
                if self.show_original.get() and seg.get("original"):
                    text = f"{seg['original']}\n{text}"
                wrapped_lines = self._wrap_text(measure_draw, text, measure_font, max_text_w)
                wrapped_text = "\n".join(wrapped_lines)
                bbox = measure_draw.multiline_textbbox((0, 0), wrapped_text, font=measure_font)
                text_h = bbox[3] - bbox[1]
                y_top = int(y_center - text_h / 2)
                y_top = max(0, min(y_top, video_height - text_h))
                ass_text = "\\N".join(wrapped_lines)
                ass_text = ass_text.replace("{", "").replace("}", "")
                positioned_text = f"{{\\an8\\pos({x_center},{y_top})}}{ass_text}"
                f.write(f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{positioned_text}\n")

    @staticmethod
    def _fmt_ass_time(seconds: float) -> str:
        """ASS 时间戳格式"""
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = int(seconds % 60)
        cs = int((seconds - int(seconds)) * 100)
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    def _switch_video_source(self, new_video_path):
        """压制完成后记录新视频，并切换播放器到新视频"""
        self.burned_video_path = new_video_path
        self.video_source.set("burned")
        self._load_video_source(new_video_path)
        self.video_name_label.config(text=os.path.basename(new_video_path), fg="black")

    def _on_video_source_change(self):
        """根据单选框切换播放器视频源"""
        if self.video_source.get() == "original":
            if not self.original_video_path:
                return
            self._load_video_source(self.original_video_path)
            self.video_name_label.config(text=os.path.basename(self.original_video_path), fg="black")
        else:
            if not self.burned_video_path or not os.path.exists(self.burned_video_path):
                self.video_source.set("original")
                self.burn_status_label.config(text="还没有生成新视频", fg="orange")
                return
            self._load_video_source(self.burned_video_path)
            self.video_name_label.config(text=os.path.basename(self.burned_video_path), fg="black")

    def _load_video_source(self, video_path):
        """加载指定视频到播放器"""
        # 停止当前播放
        self.is_playing = False
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None

        # 释放旧的
        if self.cap:
            self.cap.release()

        # 加载视频
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.current_frame_idx = 0

        self.progress_scale.config(to=self.total_frames)
        self.progress_var.set(0)
        self.play_btn.config(text="▶ 播放")

        # 显示第一帧
        self._show_frame()

    def _open_burned_video_folder(self):
        """打开新视频所在目录"""
        if not self.burned_video_path or not os.path.exists(self.burned_video_path):
            self.burn_status_label.config(text="还没有生成新视频", fg="orange")
            return
        folder_path = os.path.dirname(self.burned_video_path)
        os.startfile(folder_path)

    def _toggle_play(self):
        """播放/暂停切换"""
        if not self.cap:
            return

        if self.is_playing:
            self.is_playing = False
            self.play_btn.config(text="▶ 播放")
            if self.after_id:
                self.root.after_cancel(self.after_id)
                self.after_id = None
        else:
            self.is_playing = True
            self.play_start_time = time.perf_counter()
            self.play_start_frame = self.current_frame_idx
            self.play_btn.config(text="⏸ 暂停")
            self._play_loop()

    def _stop(self):
        """停止播放，回到开头"""
        if not self.cap:
            return

        self.is_playing = False
        self.play_btn.config(text="▶ 播放")
        if self.after_id:
            self.root.after_cancel(self.after_id)
            self.after_id = None

        self.current_frame_idx = 0
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.progress_var.set(0)
        self._show_frame()

    def _on_seek(self, value):
        """进度条拖拽"""
        if not self.cap or self.is_playing:
            return
        frame_idx = int(float(value))
        if abs(frame_idx - self.current_frame_idx) > 2:
            self.current_frame_idx = frame_idx
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
            if not self.is_playing:
                self._show_frame()

    def _play_loop(self):
        """播放循环：按真实时间推进，避免渲染耗时导致慢速播放"""
        if not self.is_playing or not self.cap:
            return

        elapsed = time.perf_counter() - self.play_start_time
        target_frame = int(self.play_start_frame + elapsed * self.fps)

        if target_frame >= self.total_frames:
            self.is_playing = False
            self.current_frame_idx = max(0, self.total_frames - 1)
            self.play_btn.config(text="▶ 播放")
            return

        if target_frame < self.current_frame_idx:
            target_frame = self.current_frame_idx

        if target_frame == self.current_frame_idx and self.after_id is not None:
            self.after_id = self.root.after(5, self._play_loop)
            return

        self.current_frame_idx = target_frame
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame_idx)
        ret, frame = self.cap.read()
        if not ret:
            self.is_playing = False
            self.play_btn.config(text="▶ 播放")
            return

        self.progress_var.set(self.current_frame_idx)
        self._render_frame(frame)
        self._update_time_label()

        # 高频短间隔调度，由时间轴决定显示哪一帧
        self.after_id = self.root.after(10, self._play_loop)

    def _show_frame(self):
        """显示当前帧（不推进播放）"""
        if not self.cap:
            return

        self.cap.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame_idx)
        ret, frame = self.cap.read()
        if ret:
            self._render_frame(frame)
            self._update_time_label()

    def _render_frame(self, frame):
        """渲染视频帧 + 字幕叠加"""
        # BGR -> RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(frame_rgb)

        # 获取当前时间对应的字幕
        current_time = self.current_frame_idx / self.fps
        original_text = ""
        subtitle_text = ""

        if self.video_source.get() == "burned":
            # 新视频已经压制字幕，不再叠加预览字幕，避免重复显示
            subtitle_text = ""
            original_text = ""
        elif self.bilingual_subtitles:
            for sub in self.bilingual_subtitles:
                if sub["start"] <= current_time <= sub["end"]:
                    original_text = sub.get("original", "")
                    subtitle_text = sub.get("translated") or original_text
                    break
        else:
            subtitle_text = get_subtitle_at_time(self.subtitles, current_time)

        # 如果有字幕，叠加绘制
        if subtitle_text:
            # 默认只显示译文；勾选后将原文+译文作为同一个字幕块绘制
            display_text = subtitle_text
            if self.show_original.get() and original_text:
                display_text = f"{original_text}\n{subtitle_text}"
            pil_img = self._draw_subtitle(pil_img, display_text)

        # 缩放到 canvas 大小
        canvas_w = self.canvas.winfo_width()
        canvas_h = self.canvas.winfo_height()
        if canvas_w < 10 or canvas_h < 10:
            canvas_w, canvas_h = 800, 450

        img_w, img_h = pil_img.size
        scale = min(canvas_w / img_w, canvas_h / img_h)
        new_w = int(img_w * scale)
        new_h = int(img_h * scale)

        pil_img = pil_img.resize((new_w, new_h), Image.LANCZOS)

        # 转为 Tkinter 可用的图片
        self.tk_img = ImageTk.PhotoImage(pil_img)

        # 居中显示
        x = (canvas_w - new_w) // 2
        y = (canvas_h - new_h) // 2
        self.canvas.delete("all")
        self.canvas.create_image(x, y, anchor=tk.NW, image=self.tk_img)

    def _draw_subtitle(self, img: Image.Image, text: str) -> Image.Image:
        """在图片上绘制字幕"""
        draw = ImageDraw.Draw(img)
        font_size = self.font_size.get()

        # 加载字体
        try:
            font = ImageFont.truetype(self.font_name.get(), font_size)
        except (OSError, IOError):
            try:
                font = ImageFont.truetype("msyh.ttc", font_size)
            except (OSError, IOError):
                font = ImageFont.load_default()

        img_w, img_h = img.size

        # 字幕最大宽度为视频宽度的 90%
        max_text_w = int(img_w * 0.9)

        # 自动换行：将文本按最大宽度拆分为多行
        lines = self._wrap_text(draw, text, font, max_text_w)
        wrapped_text = "\n".join(lines)

        # 计算换行后的整体尺寸
        bbox = draw.multiline_textbbox((0, 0), wrapped_text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        # 计算 Y 位置
        y_percent = self.y_position.get() / 100.0
        x = (img_w - text_w) // 2
        y = int(img_h * y_percent) - text_h // 2

        # 确保不超出边界
        y = max(0, min(y, img_h - text_h))
        x = max(0, min(x, img_w - text_w))

        # 绘制半透明灰色字幕背景框
        padding_x = max(10, font_size // 2)
        padding_y = max(6, font_size // 4)
        bg_left = max(0, x - padding_x)
        bg_top = max(0, y - padding_y)
        bg_right = min(img_w, x + text_w + padding_x)
        bg_bottom = min(img_h, y + text_h + padding_y)
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rectangle(
            (bg_left, bg_top, bg_right, bg_bottom),
            fill=(80, 80, 80, 153)
        )
        img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(img)

        # 绘制描边（黑色轮廓）
        outline_range = max(1, font_size // 16)
        for dx in range(-outline_range, outline_range + 1):
            for dy in range(-outline_range, outline_range + 1):
                if dx == 0 and dy == 0:
                    continue
                draw.multiline_text((x + dx, y + dy), wrapped_text, font=font,
                                    fill="#000000", align="center")

        # 绘制字幕文本
        draw.multiline_text((x, y), wrapped_text, font=font,
                            fill=self.font_color, align="center")

        return img

    @staticmethod
    def _wrap_text(draw, text: str, font, max_width: int) -> list:
        """将文本按最大宽度自动换行"""
        # 如果文本本身包含换行符，先按换行符拆分再处理每行
        paragraphs = text.split("\n")
        lines = []
        for para in paragraphs:
            if not para:
                lines.append("")
                continue
            current_line = ""
            for char in para:
                test_line = current_line + char
                bbox = draw.textbbox((0, 0), test_line, font=font)
                if bbox[2] - bbox[0] <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = char
            if current_line:
                lines.append(current_line)
        return lines

    def _update_time_label(self):
        """更新时间显示"""
        current_sec = self.current_frame_idx / self.fps
        total_sec = self.total_frames / self.fps
        self.time_label.config(
            text=f"{self._fmt_time(current_sec)} / {self._fmt_time(total_sec)}"
        )

    @staticmethod
    def _fmt_time(seconds: float) -> str:
        """格式化时间为 MM:SS"""
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m:02d}:{s:02d}"

    def on_close(self):
        """关闭窗口时释放资源"""
        self.is_playing = False
        if self.after_id:
            self.root.after_cancel(self.after_id)
        if self.cap:
            self.cap.release()
        self.root.destroy()


def main():
    root = tk.Tk()
    app = SubtitlePreviewApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
