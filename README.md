# videoTransfer

`videoTransfer` 是一个视频字幕识别、翻译、预览与硬字幕压制工具。项目支持从视频中提取音频，通过 Whisper 进行语音识别（ASR），再调用 DeepSeek 等 OpenAI 兼容接口完成字幕纠错与翻译，最终输出双语 SRT 字幕文件，或将译文字幕烧录到视频中。

项目同时提供：

- **图形界面模式**：通过 `gui_app.py` 进行视频选择、字幕预览、样式调整、重新翻译和字幕压制。
- **命令行模式**：通过 `subtitle_translator.py` 执行视频转字幕、翻译和可选硬字幕烧录。

## 主要功能

- **视频音频提取**：使用 ffmpeg 从视频中提取 16kHz、单声道 WAV 音频。
- **语音识别**：使用 OpenAI Whisper 将音频识别为带时间轴的文本片段。
- **大模型纠错与翻译**：调用 DeepSeek API 对 Whisper 识别文本进行纠错，并翻译为目标语言。
- **双语 SRT 生成**：输出标准 SRT 文件，每条字幕包含原文和译文。
- **ASS 字幕生成**：为硬字幕压制生成带样式的 ASS 字幕文件。
- **硬字幕压制**：调用 ffmpeg 将 ASS 字幕烧录到视频画面中。
- **字幕预览 GUI**：支持打开视频、打开字幕、实时预览字幕、调整字体大小/颜色/Y 轴位置。
- **重新翻译**：支持读取磁盘上已人工修改过的 SRT 文件，并基于最新原文重新翻译。
- **视频源切换**：GUI 中可在原视频和压制后新视频之间切换播放。

## 项目结构

```text
videoTransfer/
├── core/
│   ├── __init__.py
│   ├── extractor.py           # 音频提取：调用 ffmpeg 提取 WAV 音频
│   ├── recognizer.py          # 语音识别：调用 Whisper 识别音频文本
│   ├── translator.py          # 字幕纠错与翻译：调用 OpenAI 兼容 LLM API
│   ├── srt_parser.py          # SRT 解析：支持普通字幕和双语字幕解析
│   ├── srt_writer.py          # SRT / ASS 生成
│   ├── burner.py              # 字幕烧录：调用 ffmpeg ass 滤镜压制视频
│   └── subtitle_detector.py   # 原字幕区域检测：估算字幕位置和字体大小
├── testVideo/                 # 测试视频、字幕和压制后样例视频
├── venv2/                     # 已存在的虚拟环境目录
├── python310/                 # 独立 Python 运行环境目录
├── config.py                  # LLM API 配置
├── ffmpeg.exe                 # ffmpeg 二进制文件
├── ffprobe.exe                # ffprobe 二进制文件
├── gui_app.py                 # Tkinter 图形界面入口
├── subtitle_translator.py     # 命令行字幕翻译入口
├── requirements.txt           # Python 依赖声明
└── README.md                  # 项目说明文档
```

## 运行环境

### 基础环境

- **操作系统**：Windows 环境优先。
- **Python**：建议 Python 3.10 或项目内置的 `python310/` 环境。
- **ffmpeg / ffprobe**：项目根目录已包含 `ffmpeg.exe` 和 `ffprobe.exe`；如果不存在，则需要将 ffmpeg 加入系统 PATH。
- **LLM API**：需要可用的 DeepSeek API Key，或其他兼容 OpenAI SDK 的接口配置。

### Python 依赖

`requirements.txt` 当前列出的依赖：

```text
openai-whisper
openai
opencv-python
pillow
numpy
```

安装依赖：

```powershell
python -m pip install -r requirements.txt
```

说明：`ffmpeg` 是外部二进制工具，`ffmpeg-python` 不包含 `ffmpeg.exe`。项目可使用根目录下的 `ffmpeg.exe`，或使用系统 PATH 中已安装的 ffmpeg。

如果使用项目已有虚拟环境，可先激活：

```powershell
.\venv2\Scripts\Activate.ps1
```

然后安装依赖：

```powershell
python -m pip install -r requirements.txt
```

## 配置说明

LLM 配置位于本地 `config.py`，请在本机填写自己的 DeepSeek API Key：

```python
LLM_API_KEY = "请在本地 config.py 中填写你的 DeepSeek API Key"
LLM_BASE_URL = "https://api.deepseek.com"
LLM_MODEL = "deepseek-chat"
```

如果需要临时指定 Key，也可以在命令行运行时通过 `--api-key` 参数传入：

```powershell
python subtitle_translator.py -i .\testVideo\2025106-158586.mp4 -t en --api-key "你的 DeepSeek API Key"
```

说明：

- **不要把真实 API Key 写入 README**：README 通常会被提交到代码仓库或转发给他人，写入真实 Key 会导致密钥泄露。
- **推荐写法**：真实 Key 只保存在本地 `config.py`、环境变量或私有配置文件中。
- **命令行优先级**：`subtitle_translator.py` 支持通过 `--api-key` 参数临时传入 API Key，优先级高于 `config.py`。
- **账户余额**：DeepSeek API Key 必须有效且账户余额充足，否则翻译流程会失败。

## 启动 GUI

在项目根目录执行：

```powershell
python gui_app.py
```

GUI 主要操作流程：

1. 点击 **打开视频文件**，选择待处理视频。
2. 选择目标语言，如英语、法语、德语、日语、西班牙语。
3. 点击 **开始翻译**，程序会调用命令行翻译流程生成同名 `.srt` 文件。
4. 翻译完成后，SRT 会被自动加载，并使用记事本打开，方便人工审核。
5. 可点击 **打开译文字幕文件** 手动加载 SRT。
6. 可调整字幕字体、字号、颜色、Y 轴位置，以及是否显示中文原文。
7. 点击 **应用**，刷新 GUI 预览字幕样式。
8. 点击 **字幕压制**，将当前字幕样式烧录到新视频。
9. 压制完成后，GUI 会切换到新视频；也可以在 **原视频 / 新视频** 间切换。
10. 点击文件夹按钮可打开新视频所在目录。

## 命令行使用

### 只生成 SRT 字幕

```powershell
python subtitle_translator.py -i .\testVideo\2025106-158586.mp4 -t en
```

默认输出：

```text
原视频同目录/原文件名.srt
```

### 生成 SRT 并输出指定路径

```powershell
python subtitle_translator.py -i .\testVideo\2025106-158586.mp4 -t ja -o .\testVideo\output.srt
```

### 识别并压制硬字幕

```powershell
python subtitle_translator.py -i .\testVideo\2025106-158586.mp4 -t en --burn
```

默认输出：

```text
原视频同目录/原文件名_translated.mp4
```

### 压制时同时显示原文

```powershell
python subtitle_translator.py -i .\testVideo\2025106-158586.mp4 -t en --burn --show-original
```

默认情况下，硬字幕压制只显示译文，避免和视频原有字幕重叠。加上 `--show-original` 后，会同时压制原文和译文。

### 指定 Whisper 模型

```powershell
python subtitle_translator.py -i .\testVideo\2025106-158586.mp4 -t ko -m small
```

支持的模型：

- `tiny`
- `base`（默认）
- `small`
- `medium`
- `large`

模型越大，识别效果通常越好，但运行速度越慢、资源占用越高。

### 常用参数

| 参数 | 说明 |
| --- | --- |
| `-i`, `--input` | 输入视频文件路径，必填 |
| `-t`, `--target-lang` | 目标语言代码，默认 `en` |
| `-s`, `--source-lang` | 源语言代码，默认自动检测 |
| `-m`, `--model` | Whisper 模型大小，默认 `base` |
| `-o`, `--output` | 输出路径，不传则自动生成 |
| `--burn` | 将字幕烧录到视频中 |
| `--show-original` | 烧录时同时显示原文 |
| `--api-key` | 临时传入 LLM API Key |
| `--no-timeline` | 不在控制台输出字幕时间轴 |

支持的目标语言代码包括：

| 语言代码 | 语言名称 | GUI 下拉框名称 |
| --- | --- | --- |
| `en` | 英语 / English | 英语 |
| `zh-cn` | 简体中文 | 简体中文 |
| `zh-tw` | 繁体中文 | 繁体中文 |
| `ja` | 日语 / Japanese | 日语 |
| `ko` | 韩语 / Korean | 韩语 |
| `fr` | 法语 / French | 法语 |
| `de` | 德语 / German | 德语 |
| `es` | 西班牙语 / Spanish | 西班牙语 |
| `ru` | 俄语 / Russian | 俄语 |
| `pt` | 葡萄牙语 / Portuguese | 葡萄牙语 |
| `it` | 意大利语 / Italian | 意大利语 |
| `ar` | 阿拉伯语 / Arabic | 阿拉伯语 |
| `hi` | 印地语 / Hindi | 印地语 |
| `th` | 泰语 / Thai | 泰语 |
| `vi` | 越南语 / Vietnamese | 越南语 |

GUI 的目标语言下拉框已同步显示以上全部语言。

## 核心流程

### 命令行处理流程

```text
输入视频
  ↓
extractor.py：提取 WAV 音频
  ↓
recognizer.py：Whisper 语音识别
  ↓
translator.py：大模型纠错 + 翻译
  ↓
srt_writer.py：生成双语 SRT
  ↓
可选：subtitle_detector.py 检测字幕位置
  ↓
可选：srt_writer.py 生成 ASS
  ↓
可选：burner.py 调用 ffmpeg 压制视频
```

### GUI 处理流程

```text
打开视频
  ↓
开始翻译 / 打开已有字幕
  ↓
加载 SRT 并实时预览
  ↓
调整字幕样式
  ↓
应用预览
  ↓
字幕压制
  ↓
生成 原文件名_burned.mp4
  ↓
切换到新视频预览
```

### 重新翻译流程

GUI 的 **重新翻译** 功能不会重新进行语音识别，而是：

1. 根据当前原视频路径查找同名 `.srt` 文件。
2. 从磁盘重新读取最新 SRT 内容，确保包含用户手动编辑后的字幕。
3. 提取每条字幕的中文原文。
4. 调用 `translate_segments()` 重新翻译。
5. 覆盖写回同名 SRT 文件。
6. 重新加载字幕，并用记事本打开供审核。

## 输出文件规则

| 操作 | 默认输出 |
| --- | --- |
| 命令行生成字幕 | `原文件名.srt` |
| 命令行压制视频 | `原文件名_translated.mp4` |
| GUI 压制视频 | `原文件名_burned.mp4` |
| 临时音频 | 系统临时目录中的 `*_audio.wav`，流程结束后自动清理 |
| 临时 ASS | `*_temp.ass` 或 `*_gui_burn.ass`，压制后自动清理 |

## 测试素材

测试文件位于 `testVideo/`：

```text
testVideo/
├── 2025106-115648.mp4
├── 2025106-115648.srt
├── 2025106-115648_burned.mp4
├── 2025106-158586.mp4
├── 2025106-158586.srt
└── 2025106-158586_burned.mp4
```

可以直接在 GUI 中打开这些视频和字幕文件，用于验证字幕预览、重新翻译和压制效果。

## 字幕显示与压制规则

- **SRT 格式**：每条字幕默认先写原文，再写译文。
- **GUI 预览**：默认显示译文；勾选“显示原文（中文）”后，会将原文和译文合并为同一个字幕块显示。
- **GUI 背景框**：预览字幕使用半透明灰色背景，提升可读性。
- **硬字幕默认行为**：命令行 `--burn` 默认只烧录译文；如需原文，使用 `--show-original`。
- **GUI 压制行为**：使用当前 GUI 中的字号、颜色、Y 轴位置和原文显示选项生成 ASS 字幕。
- **压制后预览**：切换到新视频时，GUI 不再重复叠加预览字幕，避免字幕显示两遍。

## 注意事项

- **首次运行 Whisper 较慢**：首次加载模型时可能需要下载模型文件，耗时取决于网络和模型大小。
- **ffmpeg-python 不包含 ffmpeg 二进制**：项目已带 `ffmpeg.exe`，如果移动项目文件，需要确保 ffmpeg 仍可用。
- **API Key 安全**：不要把真实 Key 写入公开仓库，建议使用环境变量或本地私有配置。
- **重新翻译依赖已有 SRT**：GUI 的重新翻译功能需要当前视频存在同名 `.srt` 文件。
- **命令行与 GUI 输出名不同**：命令行压制默认输出 `_translated.mp4`，GUI 压制默认输出 `_burned.mp4`。
- **视频格式支持**：GUI 文件选择器支持 `mp4`、`mkv`、`avi`、`mov`、`flv`。
- **字体可用性**：GUI 预设字体包括 `msyh.ttc`、`simhei.ttf`、`simsun.ttc`、`arial.ttf`，需要系统中存在对应字体文件。

## 常见问题

### 1. 提示找不到 ffmpeg

确认项目根目录存在 `ffmpeg.exe`，或将 ffmpeg 安装目录加入系统 PATH。

### 2. 翻译失败或 API 调用失败

检查：

- `config.py` 中的 API Key 是否有效。
- DeepSeek 账户是否有余额。
- 网络是否可访问 `https://api.deepseek.com`。
- 是否需要通过 `--api-key` 临时传入新的 Key。

### 3. GUI 打开后无法显示视频

检查：

- 视频路径是否存在。
- OpenCV 是否安装：`python -m pip install opencv-python`。
- 视频编码是否被当前 OpenCV/ffmpeg 环境支持。

### 4. 字幕没有叠加显示

检查：

- 是否已加载 SRT 文件。
- SRT 时间轴是否和视频时间匹配。
- 当前是否切换到了“新视频”源；新视频源默认不再额外叠加字幕。

### 5. 重新翻译不是基于最新修改内容

重新翻译前请先保存记事本中的 SRT 文件。程序会从磁盘重新读取同名 `.srt`，未保存的编辑内容不会生效。
