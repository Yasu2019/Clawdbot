#!/usr/bin/env python3
"""
A案: Wav2Lip リップシンク実行スクリプト
キャラクター静止画 + VOICEVOX音声 → 口パク動画
"""
import os, sys, subprocess, requests, wave, shutil

W2L_DIR  = "/home/node/clawd/apps/video_factory/wav2lip"
OUT_DIR  = "/home/node/clawd/apps/video_factory/output"
VOICEVOX = "http://voicevox:50021"
SPEAKER  = 81
FPS      = 25  # Wav2Lipデフォルト

face_img  = f"{OUT_DIR}/character_face.png"
audio_out = f"{OUT_DIR}/wav2lip_audio.wav"
face_vid  = f"{OUT_DIR}/face_static.mp4"
result    = f"{OUT_DIR}/metal_lipsync.mp4"

# 1. TTS生成（シーン1+2を使用）
print("🎙️  VOICEVOX TTS生成中...")
text = "烈火の魂よ。激情の若者よ、世界に叫べ。恐れるな、前に進め。鋼の意志で闇を切り裂け。"
r = requests.post(f"{VOICEVOX}/audio_query",
                  params={"text": text, "speaker": SPEAKER})
r.raise_for_status()
q = r.json()
q["speedScale"] = 0.85
q["pitchScale"] = -0.06
q["intonationScale"] = 1.5
q["volumeScale"] = 1.3
r2 = requests.post(f"{VOICEVOX}/synthesis",
                   params={"speaker": SPEAKER}, json=q,
                   headers={"Content-Type": "application/json"})
r2.raise_for_status()
with open(audio_out, "wb") as f:
    f.write(r2.content)
with wave.open(audio_out) as wf:
    dur = wf.getnframes() / wf.getframerate()
print(f"   音声: {dur:.1f}秒")

# 2. 静止画から顔動画を作成
print("🖼️  顔動画生成中...")
subprocess.run([
    "ffmpeg", "-y", "-loop", "1", "-i", face_img,
    "-t", str(dur + 0.5), "-r", str(FPS),
    "-c:v", "libx264", "-pix_fmt", "yuv420p", face_vid
], check=True, capture_output=True)

# 3. Wav2Lip推論
print("💋 Wav2Lip リップシンク処理中（CPU・数分かかります）...")
repo = f"{W2L_DIR}/repo"
ckpt = f"{W2L_DIR}/checkpoints/wav2lip_gan.pth"

cmd = [
    "python3", f"{repo}/inference.py",
    "--checkpoint_path", ckpt,
    "--face", face_vid,
    "--audio", audio_out,
    "--outfile", result,
    "--pads", "0", "10", "0", "0",   # 顔領域の余白
    "--resize_factor", "1",
    "--nosmooth",
]
env = os.environ.copy()
env["PYTHONPATH"] = repo

proc = subprocess.run(cmd, capture_output=True, text=True, env=env, cwd=repo)
print("STDOUT:", proc.stdout[-500:] if proc.stdout else "")
print("STDERR:", proc.stderr[-800:] if proc.stderr else "")

if proc.returncode == 0 and os.path.exists(result):
    size = os.path.getsize(result) / 1024 / 1024
    print(f"\n✅ リップシンク完成: {result} ({size:.1f} MB)")
else:
    print(f"\n⚠️  Wav2Lip失敗（returncode={proc.returncode}）")
    print("   → アニメ顔の自動検出が困難なため、シンプル口パクモードへフォールバック")
    sys.exit(1)
