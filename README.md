# VoxMend

**让嘈杂视频中的对话更清晰。 / Clearer dialogue in noisy video.**

[中文](#中文) · [English](#english)

VoxMend 是一个面向视频的语音增强工具。它使用 [MossFormer2_SE_48K](https://huggingface.co/alibabasglab/MossFormer2_SE_48K) 降低背景噪声，输出增强后的 WAV 音频和保留原始画面码流的 MOV 视频。项目使用现有的开源模型权重，没有重新训练模型。

VoxMend is a video speech enhancement tool built around the existing [MossFormer2_SE_48K](https://huggingface.co/alibabasglab/MossFormer2_SE_48K) checkpoint. It reduces background noise, exports enhanced WAV audio, and produces a MOV with the original video stream copied without re-encoding. This project does not retrain the model.

## 中文

### 项目背景

手机或相机在餐厅、街道等环境中录制的对话，常被持续的环境噪声掩盖。VoxMend 将语音增强、音视频重新封装和结果校验串成一个批处理流程，适合需要保留原画面质量、同时改善对话可听度的视频。

### 功能

- 批量处理 `.mov`、`.mp4` 和 `.m4v` 视频，也可指定单个或多个文件。
- 从第一条音轨提取音频，转换为 48 kHz 单声道，使用 MossFormer2_SE_48K 增强语音。
- 同时输出 48 kHz WAV 和带 AAC 音轨的 MOV；视频码流直接复制，不重新编码画面。
- 优先使用媒体中的拍摄时间生成文件名；时间缺失时回退到文件修改时间，并在索引中标明。
- 核对输出的视频编码、分辨率、时长、音频采样率和拍摄时间，在 `index.csv` 中记录每个文件的处理状态。
- 保留输入文件；已有输出只有在指定 `--overwrite` 时才会被替换。

### 环境依赖

- Python 3.11 或 3.12，及 `pip`。
- 可从命令行调用的 `ffmpeg` 和 `ffprobe`。
- `requirements.txt` 中的 Python 依赖；其中 `clearvoice` 提供模型推理接口。
- `checkpoints/MossFormer2_SE_48K/last_best_checkpoint.pt` 模型权重，约 211 MiB。通过 Git 获取项目时需要 Git LFS 下载完整权重。

### 安装

在项目根目录运行：

```bash
git lfs pull                    # 通过 Git 克隆项目时，获取完整模型权重
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
```

确认 `ffmpeg -version` 与 `ffprobe -version` 均可运行。若模型文件只有几百字节，它仍是 Git LFS 指针，需要安装 Git LFS 并重新运行 `git lfs pull`。

### 使用

将视频放入项目根目录的 `input/`，然后运行：

```bash
mkdir -p input
python enhance.py
```

也可以指定文件或目录：

```bash
python enhance.py /path/to/video.mov
python enhance.py /path/to/a.mov /path/to/b.mp4 --output-dir /path/to/results
python enhance.py --input-dir /path/to/videos --output-dir /path/to/results
```

重复处理已有结果时使用 `--overwrite`。完整参数见 `python enhance.py --help`。

每个输入视频对应两个输出：

| 文件 | 内容 |
| --- | --- |
| `output/YYYYMMDD_HHMMSS_<原名>_dialogue_enhanced.wav` | 增强后的 48 kHz 单声道音频 |
| `output/YYYYMMDD_HHMMSS_<原名>_dialogue_enhanced.mov` | 原视频码流与增强后的 AAC 音频 |

`output/index.csv` 记录源文件、拍摄时间及来源、输出文件、输入输出时长、状态和错误。文件名前缀使用中国标准时间（UTC+08:00）。若媒体没有可用的拍摄时间，`time_source` 列会显示 `file_mtime`。任一文件处理失败时，命令返回非零退出码。

### 适用边界

MossFormer2_SE_48K 用于语音增强和背景噪声抑制，**不是指定说话人提取模型**。多人同时讲话时，它不能可靠地只保留其中一人；音乐和环境声也可能被改变。建议试听结果，尤其留意重叠讲话、音乐及安静片段。较长视频在 CPU 上可能需要更多处理时间。

脚本会尝试保留源视频中的 QuickTime 数据轨道；若 FFmpeg 无法复制，便在不包含这些数据轨道的情况下重新封装。原始输入不会被修改。

### 模型来源与许可证

模型权重来自 [alibabasglab/MossFormer2_SE_48K](https://huggingface.co/alibabasglab/MossFormer2_SE_48K)，推理接口来自 [ClearerVoice-Studio](https://github.com/modelscope/ClearerVoice-Studio)。权重及本项目代码按 [Apache License 2.0](LICENSE) 分发；来源与版权说明见 [NOTICE](NOTICE)。本项目不包含训练数据、原始视频或处理成片。

## English

### Background

Dialogue recorded on a phone or camera in restaurants, streets, and similar spaces can be masked by persistent background noise. VoxMend combines speech enhancement, video remuxing, and output checks in one batch workflow while preserving the original encoded video stream.

### Features

- Process `.mov`, `.mp4`, and `.m4v` videos in a batch or select individual files.
- Extract the first audio stream, convert it to 48 kHz mono, and enhance it with MossFormer2_SE_48K.
- Export both a 48 kHz WAV and a MOV with AAC audio. The video stream is copied without re-encoding.
- Use the media capture timestamp in output names, or the file modification time when metadata is unavailable.
- Check the output video codec, resolution, duration, audio sample rate, and timestamp; record each result in `index.csv`.
- Leave inputs untouched and protect existing outputs unless `--overwrite` is supplied.

### Requirements

- Python 3.11 or 3.12 and `pip`.
- `ffmpeg` and `ffprobe` available on `PATH`.
- The Python packages in `requirements.txt`; `clearvoice` provides model inference.
- The approximately 211 MiB checkpoint at `checkpoints/MossFormer2_SE_48K/last_best_checkpoint.pt`. Git LFS is needed to retrieve the full checkpoint from a Git clone.

### Installation

From the project root:

```bash
git lfs pull                    # Fetch the full checkpoint after cloning with Git
python3 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
python -m pip install -r requirements.txt
```

Check that `ffmpeg -version` and `ffprobe -version` work. A checkpoint file only a few hundred bytes long is an LFS pointer; install Git LFS and rerun `git lfs pull`.

### Usage

Place videos in `input/` at the project root and run:

```bash
mkdir -p input
python enhance.py
```

You can also select files or directories:

```bash
python enhance.py /path/to/video.mov
python enhance.py /path/to/a.mov /path/to/b.mp4 --output-dir /path/to/results
python enhance.py --input-dir /path/to/videos --output-dir /path/to/results
```

Use `--overwrite` to replace existing outputs. Run `python enhance.py --help` for all options.

Each input produces two files:

| File | Contents |
| --- | --- |
| `output/YYYYMMDD_HHMMSS_<name>_dialogue_enhanced.wav` | Enhanced 48 kHz mono audio |
| `output/YYYYMMDD_HHMMSS_<name>_dialogue_enhanced.mov` | Original video stream with enhanced AAC audio |

`output/index.csv` records source paths, capture timestamps and their provenance, output names, input and output durations, status, and errors. Filename timestamps use China Standard Time (UTC+08:00). If media metadata has no usable capture time, `time_source` is `file_mtime`. The command exits with a nonzero status if any file fails.

### Limitations

MossFormer2_SE_48K enhances speech and suppresses background noise. It is **not a target-speaker extraction model** and cannot reliably retain only one speaker when voices overlap. Music and ambience may also change. Listen to the output, especially during overlapping speech, music, and quiet passages. Long videos may take longer on CPU.

The script attempts to copy QuickTime data tracks. If FFmpeg cannot copy them, it remuxes the output without those tracks. Source files are never modified.

### Model and license

The checkpoint comes from [alibabasglab/MossFormer2_SE_48K](https://huggingface.co/alibabasglab/MossFormer2_SE_48K), and inference uses [ClearerVoice-Studio](https://github.com/modelscope/ClearerVoice-Studio). The checkpoint and this project's code are distributed under [Apache License 2.0](LICENSE); see [NOTICE](NOTICE) for provenance and copyright information. Training data, source videos, and processed media are not included.
