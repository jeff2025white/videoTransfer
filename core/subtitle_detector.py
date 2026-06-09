"""
原字幕检测模块 - 分析视频帧，检测已有字幕的位置和字体大小
"""
import cv2
import numpy as np


def detect_subtitle_region(video_path: str, sample_count: int = 20) -> dict:
    """
    检测视频中原有字幕的位置和字体大小。

    通过采样多帧画面，对底部区域进行文字轮廓分析，
    确定字幕的 y 坐标位置和估算字体像素大小。

    Args:
        video_path: 视频文件路径
        sample_count: 采样帧数

    Returns:
        {
            "y_top": int,          # 字幕区域顶部 y 坐标
            "y_bottom": int,       # 字幕区域底部 y 坐标
            "font_size": int,      # 估算的字体大小（像素）
            "video_height": int,   # 视频高度
            "video_width": int,    # 视频宽度
            "detected": bool       # 是否成功检测到字幕
        }
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError(f"无法打开视频: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(f"[字幕检测] 视频: {width}x{height}, {fps:.0f}fps, {total_frames} 帧")

    # 计算采样间隔（跳过头尾各 10%）
    start_frame = int(total_frames * 0.1)
    end_frame = int(total_frames * 0.9)
    interval = max(1, (end_frame - start_frame) // sample_count)

    # 只分析底部 30% 区域
    roi_top = int(height * 0.70)
    roi_bottom = height

    all_text_regions = []

    for i in range(sample_count):
        frame_idx = start_frame + i * interval
        if frame_idx >= total_frames:
            break

        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            continue

        # 裁剪底部区域
        roi = frame[roi_top:roi_bottom, :]

        # 检测文字区域
        text_bounds = _detect_text_in_roi(roi)
        if text_bounds:
            # 转换为全图坐标
            for (y1, y2, h) in text_bounds:
                all_text_regions.append((roi_top + y1, roi_top + y2, h))

    cap.release()

    if not all_text_regions:
        print("[字幕检测] 未检测到字幕区域，使用默认位置")
        # 默认：底部 80%-90% 区域
        default_y_top = int(height * 0.82)
        default_y_bottom = int(height * 0.92)
        default_font = int(height * 0.03)
        return {
            "y_top": default_y_top,
            "y_bottom": default_y_bottom,
            "font_size": default_font,
            "video_height": height,
            "video_width": width,
            "detected": False
        }

    # 统计分析：取中位数作为字幕位置
    y_tops = sorted([r[0] for r in all_text_regions])
    y_bottoms = sorted([r[1] for r in all_text_regions])
    heights = sorted([r[2] for r in all_text_regions])

    # 使用中位数（更稳定）
    median_y_top = y_tops[len(y_tops) // 2]
    median_y_bottom = y_bottoms[len(y_bottoms) // 2]
    median_height = heights[len(heights) // 2]

    # 字体大小约等于文字区域高度
    font_size = max(median_height, int(height * 0.02))

    print(f"[字幕检测] 检测到字幕区域: y={median_y_top}-{median_y_bottom}, "
          f"字体大小≈{font_size}px")

    return {
        "y_top": median_y_top,
        "y_bottom": median_y_bottom,
        "font_size": font_size,
        "video_height": height,
        "video_width": width,
        "detected": True
    }


def _detect_text_in_roi(roi: np.ndarray) -> list:
    """
    在 ROI 区域中检测文字轮廓，返回文字区域的 (y_top, y_bottom, height) 列表。
    """
    # 转灰度
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)

    # 二值化 - 字幕通常是亮色文字
    # 使用自适应阈值
    binary = cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY, 15, -5
    )

    # 也尝试 OTSU
    _, otsu = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # 合并两种方法
    combined = cv2.bitwise_or(binary, otsu)

    # 形态学操作：膨胀连接字符
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 3))
    dilated = cv2.dilate(combined, kernel, iterations=2)

    # 查找轮廓
    contours, _ = cv2.findContours(dilated, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    roi_h, roi_w = roi.shape[:2]
    text_regions = []

    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)

        # 过滤条件：
        # - 宽度至少为 ROI 宽度的 20%（字幕通常较长）
        # - 高度在合理范围内（字体大小通常是画面高度的 2%-8%）
        # - 不能太窄（避免噪点）
        min_width = roi_w * 0.20
        min_height = roi_h * 0.05
        max_height = roi_h * 0.40

        if w >= min_width and min_height <= h <= max_height:
            text_regions.append((y, y + h, h))

    return text_regions
