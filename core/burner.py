"""
字幕烧录模块 - 使用 ffmpeg 将 ASS 字幕烧录到视频中
"""
import os
import subprocess


def burn_subtitles(video_path: str, ass_path: str, output_path: str):
    """
    将 ASS 字幕烧录到视频中（硬字幕）。

    使用 ffmpeg 的 ass 滤镜将字幕渲染到视频画面。
    音频直接复制，视频重新编码。

    Args:
        video_path: 输入视频文件路径
        ass_path: ASS 字幕文件路径
        output_path: 输出视频文件路径
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频文件不存在: {video_path}")
    if not os.path.exists(ass_path):
        raise FileNotFoundError(f"字幕文件不存在: {ass_path}")

    # ffmpeg 路径（项目目录中的 ffmpeg）
    ffmpeg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ffmpeg.exe")
    if not os.path.exists(ffmpeg_path):
        ffmpeg_path = "ffmpeg"  # 尝试系统 PATH

    # ASS 文件路径需要转义（Windows 路径中的反斜杠和冒号）
    # ffmpeg 滤镜中路径需要用正斜杠，冒号需要转义
    ass_filter_path = ass_path.replace("\\", "/").replace(":", "\\:")

    # 构建 ffmpeg 命令
    cmd = [
        ffmpeg_path,
        "-i", video_path,
        "-vf", f"ass='{ass_filter_path}'",
        "-c:a", "copy",        # 音频直接复制
        "-c:v", "libx264",     # 视频用 H.264 编码
        "-preset", "fast",     # 编码速度
        "-crf", "23",          # 质量（越小越好，23 是默认）
        "-y",                  # 覆盖输出文件
        output_path
    ]

    print(f"[烧录] 开始将字幕烧录到视频...")
    print(f"[烧录] 输入: {video_path}")
    print(f"[烧录] 字幕: {ass_path}")
    print(f"[烧录] 输出: {output_path}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace"
        )

        if result.returncode != 0:
            # 如果带引号的路径失败，尝试不带引号
            cmd[4] = f"ass={ass_filter_path}"
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace"
            )

        if result.returncode != 0:
            error_msg = result.stderr[-500:] if result.stderr else "未知错误"
            raise RuntimeError(f"ffmpeg 烧录失败:\n{error_msg}")

        # 检查输出文件
        if not os.path.exists(output_path):
            raise RuntimeError("烧录完成但输出文件不存在")

        output_size = os.path.getsize(output_path) / (1024 * 1024)
        print(f"[烧录] 完成！输出文件: {output_path} ({output_size:.1f} MB)")

    except FileNotFoundError:
        raise RuntimeError("ffmpeg 未找到，请确保 ffmpeg.exe 在项目目录或系统 PATH 中")
