"""
视频字幕翻译工具
功能：识别视频中的语音（ASR），通过大模型纠错并翻译为指定语言，
     可输出双语 SRT 字幕文件，或将字幕烧录到视频中。

使用示例:
    python subtitle_translator.py -i video.mp4 -t en
    python subtitle_translator.py -i video.mp4 -t en --burn
    python subtitle_translator.py -i video.mp4 -t ja -m small
"""
import os
import sys
import argparse
import time

from core.extractor import extract_audio, cleanup_audio
from core.recognizer import recognize_speech
from core.translator import translate_segments
from core.srt_writer import write_srt, write_ass, print_timeline


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="视频字幕翻译工具 - 语音识别 + 大模型纠错翻译",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python subtitle_translator.py -i video.mp4 -t en
  python subtitle_translator.py -i video.mp4 -t en --burn
  python subtitle_translator.py -i video.mp4 -t ja -m small
  python subtitle_translator.py -i video.mp4 -t ko --no-timeline

支持的语言代码:
  en (英语), ja (日语), ko (韩语), zh-cn (简体中文),
  fr (法语), de (德语), es (西班牙语), ru (俄语) 等
        """
    )

    parser.add_argument("-i", "--input", required=True, help="输入视频文件路径")
    parser.add_argument("-t", "--target-lang", default="en", help="目标翻译语言 (默认: en)")
    parser.add_argument("-s", "--source-lang", default=None, help="源语言代码 (默认: 自动检测)")
    parser.add_argument("-m", "--model", default="base",
                        choices=["tiny", "base", "small", "medium", "large"],
                        help="Whisper 模型大小 (默认: base)")
    parser.add_argument("-o", "--output", default=None, help="输出文件路径 (默认: 自动生成)")
    parser.add_argument("--burn", action="store_true",
                        help="将字幕烧录到视频中（硬字幕），输出带字幕的视频文件")
    parser.add_argument("--show-original", action="store_true",
                        help="烧录时同时显示原文（默认仅烧录译文，避免与视频已有字幕重叠）")
    parser.add_argument("--api-key", default=None, help="LLM API Key (优先级高于 config.py)")
    parser.add_argument("--no-timeline", action="store_true", help="不在控制台输出时间轴")

    return parser.parse_args()


def main():
    args = parse_args()

    # 验证输入文件
    if not os.path.exists(args.input):
        print(f"错误: 视频文件不存在: {args.input}")
        sys.exit(1)

    # 确定输出路径
    base_name = os.path.splitext(args.input)[0]
    if args.output:
        output_path = args.output
    elif args.burn:
        output_path = f"{base_name}_translated.mp4"
    else:
        output_path = f"{base_name}.srt"

    total_steps = 5 if args.burn else 3

    print("=" * 60)
    print("视频字幕翻译工具 (大模型纠错+翻译)")
    print("=" * 60)
    print(f"  输入视频: {args.input}")
    print(f"  目标语言: {args.target_lang}")
    print(f"  源语言:   {args.source_lang or '自动检测'}")
    print(f"  Whisper:  {args.model}")
    print(f"  烧录模式: {'是' if args.burn else '否'}")
    print(f"  输出文件: {output_path}")
    print("=" * 60)

    start_time = time.time()
    audio_path = None
    ass_path = None

    try:
        # Step 1: 提取音频
        print(f"\n[Step 1/{total_steps}] 提取音频...")
        audio_path = extract_audio(args.input)

        # Step 2: 语音识别
        print(f"\n[Step 2/{total_steps}] 语音识别...")
        segments, detected_lang = recognize_speech(
            audio_path, model_size=args.model, source_lang=args.source_lang
        )

        if not segments:
            print("警告: 未识别到任何字幕内容")
            sys.exit(0)

        # Step 3: 大模型纠错 + 翻译
        print(f"\n[Step 3/{total_steps}] 大模型纠错 + 翻译...")
        translated = translate_segments(
            segments,
            target_lang=args.target_lang,
            source_lang=detected_lang,
            api_key=args.api_key
        )

        if args.burn:
            # Step 4: 检测原字幕位置 + 生成 ASS
            print(f"\n[Step 4/{total_steps}] 检测字幕位置 + 生成ASS...")
            from core.subtitle_detector import detect_subtitle_region
            from core.burner import burn_subtitles

            subtitle_info = detect_subtitle_region(args.input)
            ass_path = f"{base_name}_temp.ass"
            write_ass(translated, ass_path, subtitle_info, show_original=args.show_original)

            # Step 5: 烧录字幕到视频
            print(f"\n[Step 5/{total_steps}] 烧录字幕到视频...")
            burn_subtitles(args.input, ass_path, output_path)
        else:
            # 生成 SRT 文件
            write_srt(translated, output_path)

        # 输出时间轴
        if not args.no_timeline:
            print_timeline(translated)

        elapsed = time.time() - start_time
        print(f"\n完成！总耗时: {elapsed:.1f} 秒")
        print(f"输出文件: {output_path}")

    except KeyboardInterrupt:
        print("\n\n用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # 清理临时文件
        if audio_path:
            cleanup_audio(audio_path)
        if ass_path and os.path.exists(ass_path):
            os.remove(ass_path)
            print(f"[清理] 已删除临时ASS文件: {ass_path}")


if __name__ == "__main__":
    main()
