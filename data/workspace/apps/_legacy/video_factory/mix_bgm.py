#!/usr/bin/env python3
"""
BGM + VOICEVOX音声 + 映像を最終合成
voiceを前面に、BGMを背景音量で混合
"""
import subprocess, os, wave
import numpy as np

OUT_DIR = "/home/node/clawd/apps/video_factory/output"

def mix_audio(voice_path, bgm_path, out_path, voice_vol=1.0, bgm_vol=0.28):
    """WAVファイルをnumpyでミックス"""
    def load_wav(path):
        with wave.open(path) as wf:
            sr   = wf.getframerate()
            data = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        return sr, data

    sr_v, voice = load_wav(voice_path)
    sr_b, bgm   = load_wav(bgm_path)

    # BGMをVoice長に合わせてループ/トリム
    if len(bgm) < len(voice):
        repeats = (len(voice) // len(bgm)) + 1
        bgm = np.tile(bgm, repeats)
    bgm = bgm[:len(voice)]

    mixed = voice * voice_vol + bgm * bgm_vol
    mixed = np.clip(mixed, -1.0, 1.0)
    pcm   = (mixed * 32767).astype(np.int16)

    with wave.open(out_path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr_v)
        wf.writeframes(pcm.tobytes())

def make_video_with_bgm(video_in, voice_wav, bgm_wav, out_mp4, bgm_vol=0.28):
    """FFmpegでBGM込み動画を生成"""
    subprocess.run([
        "ffmpeg", "-y",
        "-i", video_in,
        "-i", voice_wav,
        "-i", bgm_wav,
        "-filter_complex",
        f"[1:a]volume=1.0[v];[2:a]volume={bgm_vol}[b];[v][b]amix=inputs=2:duration=shortest[aout]",
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-shortest", out_mp4
    ], check=True, capture_output=True)

print("🎵 BGMミックス開始...")

# C案強化版 + BGM
if os.path.exists(f"{OUT_DIR}/metal_mv_enhanced.mp4"):
    print("  C案強化版 + BGM → metal_mv_bgm.mp4")
    # 強化版の音声を抽出
    voice_tmp = f"{OUT_DIR}/voice_enhanced.wav"
    subprocess.run([
        "ffmpeg", "-y", "-i", f"{OUT_DIR}/metal_mv_enhanced.mp4",
        "-vn", "-acodec", "pcm_s16le", voice_tmp
    ], check=True, capture_output=True)

    make_video_with_bgm(
        f"{OUT_DIR}/metal_mv_enhanced.mp4",
        voice_tmp,
        f"{OUT_DIR}/metal_bgm.wav",
        f"{OUT_DIR}/metal_mv_bgm.mp4",
        bgm_vol=0.30
    )
    os.remove(voice_tmp)
    sz = os.path.getsize(f"{OUT_DIR}/metal_mv_bgm.mp4") / 1024 / 1024
    print(f"  ✅ metal_mv_bgm.mp4 ({sz:.1f}MB)")

# A案 anime + BGM
if os.path.exists(f"{OUT_DIR}/metal_anime_final.mp4"):
    print("  A案アニメ版 + BGM → metal_anime_bgm.mp4")
    voice_tmp = f"{OUT_DIR}/voice_anime.wav"
    subprocess.run([
        "ffmpeg", "-y", "-i", f"{OUT_DIR}/metal_anime_final.mp4",
        "-vn", "-acodec", "pcm_s16le", voice_tmp
    ], check=True, capture_output=True)

    make_video_with_bgm(
        f"{OUT_DIR}/metal_anime_final.mp4",
        voice_tmp,
        f"{OUT_DIR}/metal_bgm.wav",
        f"{OUT_DIR}/metal_anime_bgm.mp4",
        bgm_vol=0.28
    )
    os.remove(voice_tmp)
    sz = os.path.getsize(f"{OUT_DIR}/metal_anime_bgm.mp4") / 1024 / 1024
    print(f"  ✅ metal_anime_bgm.mp4 ({sz:.1f}MB)")

print("\n✅ BGMミックス完了")
