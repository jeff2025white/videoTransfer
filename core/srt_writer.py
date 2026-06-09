"""
字幕生成模块 - 生成 SRT 和 ASS 格式的双语字幕文件
"""
import os


def format_timestamp(seconds: float) -> str:
    """
    将秒数转换为 SRT 时间戳格式: HH:MM:SS,mmm

    Args:
        seconds: 时间（秒）

    Returns:
        格式化的时间戳字符串
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int((seconds - int(seconds)) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def write_srt(translated_segments: list, output_path: str):
    """
    将翻译结果写入 SRT 字幕文件。
    每条字幕包含原文和译文（译文在原文下方）。

    Args:
        translated_segments: 翻译后的片段列表，每个元素包含:
            start, end, original, translated
        output_path: 输出 SRT 文件路径
    """
    # 确保输出目录存在
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(output_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(translated_segments, start=1):
            start_ts = format_timestamp(seg["start"])
            end_ts = format_timestamp(seg["end"])

            # 写入序号
            f.write(f"{i}\n")
            # 写入时间轴
            f.write(f"{start_ts} --> {end_ts}\n")
            # 写入原文
            f.write(f"{seg['original']}\n")
            # 写入译文（附在原文下方）
            if seg["translated"]:
                f.write(f"{seg['translated']}\n")
            # 空行分隔
            f.write("\n")

    print(f"[SRT] 字幕文件已保存: {output_path}")


def print_timeline(translated_segments: list):
    """
    在控制台输出字幕时间轴信息。

    Args:
        translated_segments: 翻译后的片段列表
    """
    print("\n" + "=" * 60)
    print("字幕时间轴")
    print("=" * 60)

    for i, seg in enumerate(translated_segments, start=1):
        start_ts = format_timestamp(seg["start"])
        end_ts = format_timestamp(seg["end"])
        print(f"\n[{i}] {start_ts} --> {end_ts}")
        print(f"    原文: {seg['original']}")
        if seg["translated"]:
            print(f"    译文: {seg['translated']}")

    print("\n" + "=" * 60)
    print(f"共 {len(translated_segments)} 条字幕")
    print("=" * 60)


def _format_ass_timestamp(seconds: float) -> str:
    """将秒数转换为 ASS 时间戳格式: H:MM:SS.cc"""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centisecs = int((seconds - int(seconds)) * 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centisecs:02d}"


def write_ass(translated_segments: list, output_path: str, subtitle_info: dict,
              show_original: bool = False):
    """
    生成 ASS 格式字幕文件（支持样式控制）。
    默认仅烧录译文；当 show_original=True 时同时烧录原文。

    Args:
        translated_segments: 翻译后的片段列表
        output_path: 输出 ASS 文件路径
        subtitle_info: 字幕检测信息 dict，包含:
            y_top, y_bottom, font_size, video_height, video_width
        show_original: 是否同时显示原文（默认 False，仅显示译文）
    """
    video_height = subtitle_info["video_height"]
    video_width = subtitle_info["video_width"]
    orig_font_size = subtitle_info["font_size"]

    # 译文字体大小：原字幕的 80%，但不小于 16px
    trans_font_size = max(16, int(orig_font_size * 0.8))

    # 计算 MarginV（从底部算起的距离）
    # 原文 MarginV：视频高度 - 原字幕底部位置
    orig_margin_v = video_height - subtitle_info["y_bottom"]

    if show_original:
        # 同时显示原文和译文：译文在原文下方
        trans_margin_v = max(5, orig_margin_v - orig_font_size - 5)
    else:
        # 仅显示译文：放在原字幕下方（原字幕位置留给视频自带字幕）
        trans_margin_v = max(5, orig_margin_v - orig_font_size - 5)

    # 确保输出目录存在
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with open(output_path, "w", encoding="utf-8") as f:
        # ASS 文件头
        f.write("[Script Info]\n")
        f.write("ScriptType: v4.00+\n")
        f.write(f"PlayResX: {video_width}\n")
        f.write(f"PlayResY: {video_height}\n")
        f.write("WrapStyle: 0\n")
        f.write("\n")

        # 样式定义
        f.write("[V4+ Styles]\n")
        f.write("Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
                "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
                "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
                "Alignment, MarginL, MarginR, MarginV, Encoding\n")

        # 原文样式：白色，黑色描边，居中底部
        f.write(f"Style: Original,Arial,{orig_font_size},"
                f"&H00FFFFFF,&H000000FF,&H00000000,&H80000000,"
                f"1,0,0,0,100,100,0,0,1,2,1,2,20,20,{orig_margin_v},1\n")

        # 译文样式：浅黄色，黑色描边，在原文下方
        f.write(f"Style: Translation,Arial,{trans_font_size},"
                f"&H0000FFFF,&H000000FF,&H00000000,&H80000000,"
                f"0,0,0,0,100,100,0,0,1,2,1,2,20,20,{trans_margin_v},1\n")

        f.write("\n")

        # 字幕事件
        f.write("[Events]\n")
        f.write("Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")

        for seg in translated_segments:
            start_ts = _format_ass_timestamp(seg["start"])
            end_ts = _format_ass_timestamp(seg["end"])

            # 原文（仅当 show_original=True 时写入）
            if show_original:
                original = seg["original"].replace("\n", "\\N")
                f.write(f"Dialogue: 0,{start_ts},{end_ts},Original,,0,0,0,,{original}\n")

            # 译文
            if seg.get("translated") and seg["translated"] != "[翻译失败]":
                translated = seg["translated"].replace("\n", "\\N")
                f.write(f"Dialogue: 0,{start_ts},{end_ts},Translation,,0,0,0,,{translated}\n")

    print(f"[ASS] 字幕文件已保存: {output_path}")
