"""
翻译模块 - 使用大模型（DeepSeek）完成字幕纠错 + 翻译
一次调用同时完成：
1. 纠正 Whisper 语音识别中的错误
2. 翻译为目标语言
"""
import json
import time
from openai import OpenAI

# 语言名称映射（用于 Prompt）
_LANG_NAMES = {
    "en": "英文",
    "zh-cn": "简体中文",
    "zh-tw": "繁体中文",
    "ja": "日语",
    "ko": "韩语",
    "fr": "法语",
    "de": "德语",
    "es": "西班牙语",
    "ru": "俄语",
    "pt": "葡萄牙语",
    "it": "意大利语",
    "ar": "阿拉伯语",
    "hi": "印地语",
    "th": "泰语",
    "vi": "越南语",
}


def translate_segments(segments: list, target_lang: str = "en",
                       source_lang: str = None,
                       api_key: str = None, base_url: str = None,
                       model: str = None, batch_size: int = 10,
                       max_retries: int = 3) -> list:
    """
    使用大模型对字幕进行纠错 + 翻译。

    Args:
        segments: 识别结果列表，每个元素包含 start, end, text
        target_lang: 目标语言代码 (如 'en', 'ja', 'ko')
        source_lang: 源语言代码 (Whisper检测到的，如 'zh', 'en')
        api_key: LLM API Key (优先级高于 config.py)
        base_url: LLM API base URL
        model: LLM 模型名
        batch_size: 每批处理的字幕段数
        max_retries: 最大重试次数

    Returns:
        翻译后的列表，每个元素包含:
        {
            "start": 开始时间(秒),
            "end": 结束时间(秒),
            "original": 纠错后的原文,
            "translated": 翻译文本
        }
    """
    # 加载配置
    if not api_key or not base_url or not model:
        try:
            import config
            api_key = api_key or config.LLM_API_KEY
            base_url = base_url or config.LLM_BASE_URL
            model = model or config.LLM_MODEL
        except ImportError:
            raise RuntimeError("未找到 config.py 配置文件，请创建配置或通过 --api-key 参数传入")

    if not api_key or api_key == "sk-xxx":
        raise RuntimeError("请在 config.py 中设置有效的 LLM_API_KEY，或通过 --api-key 参数传入")

    # 初始化客户端
    client = OpenAI(api_key=api_key, base_url=base_url)

    target_name = _LANG_NAMES.get(target_lang.lower(), target_lang)
    source_name = _LANG_NAMES.get(source_lang, "未知语言") if source_lang else "自动检测"

    total = len(segments)
    print(f"[纠错+翻译] 使用模型: {model}")
    print(f"[纠错+翻译] 源语言: {source_name}，目标语言: {target_name}")
    print(f"[纠错+翻译] 共 {total} 段字幕，每批 {batch_size} 段")

    results = []

    # 分批处理
    for batch_start in range(0, total, batch_size):
        batch_end = min(batch_start + batch_size, total)
        batch = segments[batch_start:batch_end]

        batch_results = _process_batch(
            client, model, batch, target_name, source_name, max_retries
        )
        results.extend(batch_results)

        print(f"[纠错+翻译] 进度: {batch_end}/{total}")

    print(f"[纠错+翻译] 完成")
    return results


def _process_batch(client: OpenAI, model: str, batch: list,
                   target_name: str, source_name: str,
                   max_retries: int) -> list:
    """处理一批字幕段落"""

    # 构造输入
    input_items = []
    for i, seg in enumerate(batch):
        input_items.append({"id": i, "text": seg["text"]})

    system_prompt = f"""你是专业的字幕纠错翻译专家。你的任务：
1. 纠正语音识别产生的错误文字（如同音字错误、断句错误等），输出正确的简体中文原文
2. 将纠正后的文字翻译为{target_name}

注意事项：
- 原文语言是{source_name}的语音识别结果，可能有错别字
- 纠正时要根据上下文语义判断正确用词
- 翻译要自然流畅，适合字幕显示
- 严格按照JSON格式输出，不要添加任何额外说明"""

    user_prompt = f"""请对以下语音识别字幕进行纠错并翻译为{target_name}。

输入：
{json.dumps(input_items, ensure_ascii=False)}

请严格按以下JSON数组格式输出（不要包含markdown代码块标记）：
[{{"id": 0, "corrected": "纠正后的原文", "translated": "翻译结果"}}, ...]"""

    # 调用 API（带重试）
    for attempt in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
            )

            content = response.choices[0].message.content.strip()
            # 清理可能的 markdown 代码块标记
            if content.startswith("```"):
                content = content.split("\n", 1)[1] if "\n" in content else content[3:]
            if content.endswith("```"):
                content = content[:-3].strip()
            if content.startswith("json"):
                content = content[4:].strip()

            parsed = json.loads(content)

            # 将结果映射回原始段落
            results = []
            result_map = {item["id"]: item for item in parsed}

            for i, seg in enumerate(batch):
                if i in result_map:
                    item = result_map[i]
                    results.append({
                        "start": seg["start"],
                        "end": seg["end"],
                        "original": item.get("corrected", seg["text"]),
                        "translated": item.get("translated", "")
                    })
                else:
                    # 缺失的条目，保留原文
                    results.append({
                        "start": seg["start"],
                        "end": seg["end"],
                        "original": seg["text"],
                        "translated": ""
                    })

            return results

        except json.JSONDecodeError as e:
            if attempt < max_retries - 1:
                print(f"[纠错+翻译] JSON解析失败，重试中... ({attempt + 1}/{max_retries})")
                time.sleep(2)
            else:
                print(f"[纠错+翻译] JSON解析失败，使用原文: {e}")
                return _fallback_results(batch)

        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 3
                print(f"[纠错+翻译] API调用失败，{wait_time}秒后重试: {e}")
                time.sleep(wait_time)
            else:
                print(f"[纠错+翻译] API调用失败，使用原文: {e}")
                return _fallback_results(batch)

    return _fallback_results(batch)


def _fallback_results(batch: list) -> list:
    """失败时的兜底结果"""
    return [{
        "start": seg["start"],
        "end": seg["end"],
        "original": seg["text"],
        "translated": "[翻译失败]"
    } for seg in batch]
