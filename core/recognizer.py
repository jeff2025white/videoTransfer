"""
语音识别模块 - 使用 Whisper 模型识别音频中的语音
"""
import whisper


def recognize_speech(audio_path: str, model_size: str = "base", source_lang: str = None) -> tuple:
    """
    使用 Whisper 模型识别音频中的语音。

    Args:
        audio_path: 音频文件路径
        model_size: Whisper 模型大小 (tiny/base/small/medium/large)
        source_lang: 源语言代码 (如 'en', 'ja', 'ko')，为 None 时自动检测

    Returns:
        (segments, detected_lang) 元组:
        - segments: 识别结果列表，每个元素为 dict: {start, end, text}
        - detected_lang: 检测到的语言代码 (如 'zh', 'en', 'ja')
    """
    print(f"[语音识别] 加载 Whisper 模型: {model_size}")
    model = whisper.load_model(model_size)

    print(f"[语音识别] 开始识别...")
    options = {}
    if source_lang:
        options["language"] = source_lang

    result = model.transcribe(audio_path, **options)

    # 提取分段结果
    segments = []
    detected_lang = result.get("language", "unknown")

    for seg in result["segments"]:
        segments.append({
            "start": seg["start"],
            "end": seg["end"],
            "text": seg["text"].strip()
        })

    print(f"[语音识别] 完成，检测到语言: {detected_lang}，共 {len(segments)} 个片段")

    return segments, detected_lang
