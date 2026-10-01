#!/usr/bin/env python3
"""Enhance dialogue in videos with MossFormer2_SE_48K and copy the video stream."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent
CHECKPOINT = ROOT / "checkpoints/MossFormer2_SE_48K/last_best_checkpoint.pt"
VIDEO_EXTENSIONS = {".mov", ".mp4", ".m4v"}
CHINA_TIME = dt.timezone(dt.timedelta(hours=8))


def run(*args: str) -> str:
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip()[-2000:] or f"Command failed: {args[0]}")
    return result.stdout


def probe(path: Path) -> dict:
    return json.loads(run("ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)))


def stream(info: dict, kind: str) -> dict | None:
    return next((item for item in info.get("streams", []) if item.get("codec_type") == kind), None)


def duration(info: dict) -> float:
    value = info.get("format", {}).get("duration")
    if value is None:
        raise ValueError("Media duration is unavailable")
    return float(value)


def capture_time(info: dict, path: Path) -> tuple[dt.datetime, str]:
    tag_sets = [info.get("format", {}).get("tags", {})]
    tag_sets.extend(item.get("tags", {}) for item in info.get("streams", []))
    for tags in tag_sets:
        raw = tags.get("com.apple.quicktime.creationdate") or tags.get("creation_time")
        if raw:
            try:
                value = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
                if value.tzinfo is None:
                    value = value.replace(tzinfo=dt.timezone.utc)
                return value.astimezone(dt.timezone.utc), "metadata"
            except ValueError:
                continue
    return dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc), "file_mtime"


def mux(source: Path, audio: Path, target: Path, capture: dt.datetime) -> None:
    timestamp = capture.isoformat().replace("+00:00", "Z")
    common = (
        "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac",
        "-b:a", "256k", "-ar", "48000", "-map_metadata", "0",
        "-metadata", f"creation_time={timestamp}",
        "-metadata:s:v:0", f"creation_time={timestamp}",
        "-movflags", "+use_metadata_tags",
    )
    base = ("ffmpeg", "-y", "-v", "error", "-i", str(source), "-i", str(audio))
    try:
        run(*base, "-map", "0:d?", "-c:d", "copy", *common, str(target))
    except RuntimeError:
        # Some QuickTime data tracks cannot be copied into the output container.
        run(*base, *common, str(target))


def process(source: Path, output: Path, model: object, overwrite: bool) -> dict:
    original = probe(source)
    original_video = stream(original, "video")
    if original_video is None or stream(original, "audio") is None:
        raise ValueError("Input needs both video and audio streams")

    capture, time_source = capture_time(original, source)
    prefix = capture.astimezone(CHINA_TIME).strftime("%Y%m%d_%H%M%S")
    stem = f"{prefix}_{source.stem}_dialogue_enhanced"
    out_audio = output / f"{stem}.wav"
    out_video = output / f"{stem}.mov"
    if not overwrite and (out_audio.exists() or out_video.exists()):
        raise FileExistsError(f"Output exists for {source.name}; use --overwrite")

    with tempfile.TemporaryDirectory(prefix=".voxmend-", dir=output) as temporary:
        temporary_path = Path(temporary)
        mix = temporary_path / "input_48k.wav"
        run("ffmpeg", "-y", "-v", "error", "-i", str(source), "-map", "0:a:0",
            "-vn", "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", str(mix))
        enhanced_dir = temporary_path / "enhanced"
        model(input_path=str(mix), online_write=True, output_path=str(enhanced_dir))
        enhanced = enhanced_dir / "MossFormer2_SE_48K" / mix.name
        if not enhanced.is_file():
            raise FileNotFoundError(f"Model output missing: {enhanced}")
        staged_audio = temporary_path / "enhanced.wav"
        staged_video = temporary_path / "enhanced.mov"
        shutil.copyfile(enhanced, staged_audio)
        mux(source, staged_audio, staged_video, capture)
        result = probe(staged_video)
        result_video = stream(result, "video")
        result_audio = stream(result, "audio")
        if result_video is None or result_audio is None:
            raise ValueError("Output is missing a video or audio stream")
        for key in ("codec_name", "width", "height"):
            if result_video.get(key) != original_video.get(key):
                raise ValueError(f"Video {key} changed")
        if abs(duration(original) - duration(result)) > 0.15:
            raise ValueError("Output duration differs by more than 150 ms")
        if result_audio.get("sample_rate") != "48000":
            raise ValueError("Output audio is not 48 kHz")
        output_capture, _ = capture_time(result, staged_video)
        if abs((capture - output_capture).total_seconds()) > 1:
            raise ValueError("Output capture timestamp changed")
        os.replace(staged_audio, out_audio)
        os.replace(staged_video, out_video)

    return {
        "source": str(source), "capture_time_utc": capture.isoformat(),
        "time_source": time_source, "output_video": out_video.name,
        "output_audio": out_audio.name, "duration_in_s": f"{duration(original):.3f}",
        "duration_out_s": f"{duration(result):.3f}", "status": "OK", "error": "",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("videos", nargs="*", type=Path, help="Video files; defaults to input/.")
    parser.add_argument("--input-dir", type=Path, default=ROOT / "input")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "output")
    parser.add_argument("--overwrite", action="store_true", help="Replace existing outputs.")
    args = parser.parse_args()

    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool) is None:
            parser.error(f"Required executable not found: {tool}")
    if not CHECKPOINT.is_file():
        parser.error(f"Model checkpoint missing: {CHECKPOINT} (run git lfs pull)")
    if CHECKPOINT.stat().st_size < 100_000_000:
        parser.error(f"Model checkpoint appears to be an LFS pointer: {CHECKPOINT} (run git lfs pull)")
    paths = [path.resolve() for path in args.videos]
    if not paths:
        if not args.input_dir.is_dir():
            parser.error(f"Input directory does not exist: {args.input_dir}")
        paths = sorted(path.resolve() for path in args.input_dir.iterdir()
                       if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS)
    if not paths:
        parser.error("No videos found")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_dir = args.output_dir.resolve()

    # ClearVoice resolves its checkpoint relative to the current directory.
    os.chdir(ROOT)
    from clearvoice import ClearVoice
    model = ClearVoice(task="speech_enhancement", model_names=["MossFormer2_SE_48K"])
    rows = []
    for source in paths:
        print(f"Processing {source.name}...", flush=True)
        try:
            row = process(source, output_dir, model, args.overwrite)
        except Exception as exc:
            row = {
                "source": str(source), "capture_time_utc": "", "time_source": "",
                "output_video": "", "output_audio": "", "duration_in_s": "",
                "duration_out_s": "", "status": "FAILED", "error": str(exc),
            }
        rows.append(row)
        print(f"{row['status']}: {source.name} {row['error']}", flush=True)

    columns = ("source", "capture_time_utc", "time_source", "output_video",
               "output_audio", "duration_in_s", "duration_out_s", "status", "error")
    with (output_dir / "index.csv").open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    print(f"Completed: {sum(row['status'] == 'OK' for row in rows)}/{len(rows)}; "
          f"index: {output_dir / 'index.csv'}")
    return 0 if all(row["status"] == "OK" for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
