"""
SRT 字幕解析器 - 用于 GUI 播放器实时字幕显示
"""
import re


def parse_srt(file_path: str) -> list:
    """
    解析 SRT 文件，返回字幕段列表。

    Returns:
        [{"start": float, "end": float, "text": str}, ...]
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # 按空行分隔字幕块
    blocks = re.split(r"\n\s*\n", content.strip())
    subtitles = []

    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue

        # 第二行是时间轴
        time_line = lines[1]
        match = re.match(
            r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})",
            time_line
        )
        if not match:
            continue

        h1, m1, s1, ms1, h2, m2, s2, ms2 = [int(x) for x in match.groups()]
        start = h1 * 3600 + m1 * 60 + s1 + ms1 / 1000.0
        end = h2 * 3600 + m2 * 60 + s2 + ms2 / 1000.0

        # 第三行及之后是字幕文本
        text = "\n".join(lines[2:])
        subtitles.append({"start": start, "end": end, "text": text})

    return subtitles


def parse_srt_bilingual(file_path: str) -> list:
    """
    解析双语 SRT 文件，分离原文和译文。
    假设每条字幕第一行为原文（中文），第二行为译文。

    Returns:
        [{"start": float, "end": float, "original": str, "translated": str}, ...]
    """
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    blocks = re.split(r"\n\s*\n", content.strip())
    subtitles = []

    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue

        time_line = lines[1]
        match = re.match(
            r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})",
            time_line
        )
        if not match:
            continue

        h1, m1, s1, ms1, h2, m2, s2, ms2 = [int(x) for x in match.groups()]
        start = h1 * 3600 + m1 * 60 + s1 + ms1 / 1000.0
        end = h2 * 3600 + m2 * 60 + s2 + ms2 / 1000.0

        text_lines = lines[2:]
        if len(text_lines) >= 2:
            original = text_lines[0]
            translated = "\n".join(text_lines[1:])
        else:
            original = text_lines[0] if text_lines else ""
            translated = ""

        subtitles.append({
            "start": start, "end": end,
            "original": original, "translated": translated
        })

    return subtitles


def get_subtitle_at_time(subtitles: list, current_time: float) -> str:
    """
    根据当前播放时间，查找对应的字幕文本。

    Args:
        subtitles: parse_srt() 返回的列表
        current_time: 当前播放时间（秒）

    Returns:
        当前时间对应的字幕文本，无字幕时返回空字符串
    """
    for sub in subtitles:
        if sub["start"] <= current_time <= sub["end"]:
            return sub["text"]
    return ""
