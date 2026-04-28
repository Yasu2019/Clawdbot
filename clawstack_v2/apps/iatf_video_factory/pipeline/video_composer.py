"""FFmpeg — PNG連番 + WAV音声 → MP4合成。"""
import subprocess, json
from pathlib import Path


def merge_audio_tracks(audio_timeline: list[dict], total_sec: float, out_path: Path) -> bool:
    """複数WAVを遅延合成して1本のマスター音声WAVを作る。"""
    if not audio_timeline:
        return False

    filter_parts = []
    inputs = []
    for i, entry in enumerate(audio_timeline):
        inputs += ["-i", entry["wav"]]
        delay_ms = int(entry["start_sec"] * 1000)
        filter_parts.append(f"[{i}]adelay={delay_ms}|{delay_ms}[a{i}]")

    mix_inputs = "".join(f"[a{i}]" for i in range(len(audio_timeline)))
    filter_parts.append(f"{mix_inputs}amix=inputs={len(audio_timeline)}:duration=longest[aout]")

    cmd = (
        ["ffmpeg", "-y"]
        + inputs
        + ["-filter_complex", ";".join(filter_parts)]
        + ["-map", "[aout]", "-t", str(total_sec), str(out_path)]
    )
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        print("FFmpeg audio merge error:", result.stderr[-1000:])
        return False
    return True


def compose_video(
    frames_dir: Path,
    audio_path: Path,
    output_mp4: Path,
    fps: int = 30,
) -> bool:
    """Blender出力PNG連番 + 合成音声 → MP4。"""
    frame_pattern = str(frames_dir / "frame_%04d.png")
    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(fps),
        "-i", frame_pattern,
        "-i", str(audio_path),
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "medium",
        "-c:a", "aac",
        "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        str(output_mp4),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    if result.returncode != 0:
        print("FFmpeg compose error:", result.stderr[-1000:])
        return False
    return True


def replace_segment(
    source_mp4: Path,
    patch_mp4: Path,
    start_sec: float,
    end_sec: float,
    output_mp4: Path,
) -> bool:
    """source_mp4の[start_sec, end_sec]区間をpatch_mp4で置換して出力する。"""
    duration = end_sec - start_sec
    filter_complex = (
        f"[0:v]trim=0:{start_sec},setpts=PTS-STARTPTS[v0];"
        f"[1:v]trim=0:{duration},setpts=PTS-STARTPTS[v1];"
        f"[0:v]trim={end_sec},setpts=PTS-STARTPTS[v2];"
        f"[v0][v1][v2]concat=n=3:v=1:a=0[vout];"
        f"[0:a]atrim=0:{start_sec},asetpts=PTS-STARTPTS[a0];"
        f"[1:a]atrim=0:{duration},asetpts=PTS-STARTPTS[a1];"
        f"[0:a]atrim={end_sec},asetpts=PTS-STARTPTS[a2];"
        f"[a0][a1][a2]concat=n=3:v=0:a=1[aout]"
    )
    cmd = [
        "ffmpeg", "-y",
        "-i", str(source_mp4),
        "-i", str(patch_mp4),
        "-filter_complex", filter_complex,
        "-map", "[vout]", "-map", "[aout]",
        "-c:v", "libx264", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        str(output_mp4),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
    if result.returncode != 0:
        print("FFmpeg replace_segment error:", result.stderr[-1000:])
        return False
    return True
