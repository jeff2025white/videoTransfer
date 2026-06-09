"""
音频提取模块 - 从视频文件中提取音频轨道
"""
import os
import tempfile
import subprocess

# ffmpeg 路径：优先使用项目目录中的 ffmpeg
_PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FFMPEG_PATH = os.path.join(_PROJECT_DIR, "ffmpeg.exe") if os.path.exists(
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ffmpeg.exe")
) else "ffmpeg"


def extract_audio(video_path: str, output_path: str = None) -> str:
    """
    从视频文件中提取音频为 WAV 格式。

    Args:
        video_path: 视频文件路径
        output_path: 输出音频文件路径，为 None 时自动生成临时文件

    Returns:
        输出的音频文件路径
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"视频文件不存在: {video_path}")

    if output_path is None:
        # 生成临时文件路径
        temp_dir = tempfile.gettempdir()
        base_name = os.path.splitext(os.path.basename(video_path))[0]
        output_path = os.path.join(temp_dir, f"{base_name}_audio.wav")

    # 使用 ffmpeg 提取音频
    cmd = [
        _FFMPEG_PATH,
        "-i", video_path,
        "-vn",                  # 不处理视频
        "-acodec", "pcm_s16le", # PCM 16bit 编码
        "-ar", "16000",         # 采样率 16kHz (Whisper 推荐)
        "-ac", "1",             # 单声道
        "-y",                   # 覆盖已有文件
        output_path
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True
        )
        print(f"[提取音频] 完成: {output_path}")
        return output_path
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"音频提取失败: {e.stderr.decode('utf-8', errors='ignore')}")
    except FileNotFoundError:
        raise RuntimeError("未找到 ffmpeg，请确保已安装 ffmpeg 并添加到系统 PATH 中")


def cleanup_audio(audio_path: str):
    """清理临时音频文件"""
    if audio_path and os.path.exists(audio_path):
        os.remove(audio_path)
        print(f"[清理] 已删除临时音频文件: {audio_path}")
