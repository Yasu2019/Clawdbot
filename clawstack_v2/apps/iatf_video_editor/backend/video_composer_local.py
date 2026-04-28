"""video_composer の replace_segment をエディタ用にローカル提供。"""
import subprocess
from pathlib import Path


def replace_segment(
    source_mp4: Path,
    patch_mp4: Path,
    start_sec: float,
    end_sec: float,
    output_mp4: Path,
) -> bool:
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
