#!/usr/bin/env python3
"""
AI Video Factory - ヘビーメタル ショート動画サンプル生成
18歳男性 / VOICEVOX 青山龍星・熱血 / 9:16 / 30秒
"""
import os, json, requests, subprocess, struct, wave, io
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math, random, shutil

# ── 設定 ────────────────────────────────────────────────────
OUT_DIR    = "/home/node/clawd/apps/video_factory/output"
FONT_PATH  = "/usr/share/fonts/opentype/ipaexfont-gothic/ipaexg.ttf"
VOICEVOX   = "http://voicevox:50021"
SPEAKER_ID = 81          # 青山龍星 / 熱血
W, H       = 1080, 1920  # 9:16
FPS        = 24
os.makedirs(OUT_DIR, exist_ok=True)

# ── シナリオ ─────────────────────────────────────────────────
SCENES = [
    {"text": "烈火の魂",          "sub": "SOUL OF RAGING FIRE",    "dur": 3.0, "color": (255,40,0)},
    {"text": "激情の若者よ\n世界に叫べ", "sub": "SCREAM AT THE WORLD",   "dur": 5.0, "color": (220,30,30)},
    {"text": "恐れるな\n前に進め",   "sub": "FEAR NOTHING",            "dur": 5.0, "color": (255,80,0)},
    {"text": "鋼の意志で\n闇を切り裂け","sub": "TEAR THROUGH DARKNESS",  "dur": 6.0, "color": (200,20,60)},
    {"text": "烈火よ燃えろ\n魂の限り", "sub": "BURN WITH ALL YOUR SOUL", "dur": 6.0, "color": (255,50,20)},
    {"text": "限界を超えろ\nお前は最強だ","sub": "SURPASS YOUR LIMITS",   "dur": 5.0, "color": (220,10,10)},
]

# ── VOICEVOX TTS ─────────────────────────────────────────────
def tts(text: str, path: str):
    clean = text.replace("\n", "。")
    r = requests.post(f"{VOICEVOX}/audio_query",
                      params={"text": clean, "speaker": SPEAKER_ID})
    r.raise_for_status()
    query = r.json()
    query["speedScale"]      = 0.88   # 少し遅め（力強く）
    query["pitchScale"]      = -0.06  # 低め（重厚感）
    query["intonationScale"] = 1.6    # 抑揚強め
    query["volumeScale"]     = 1.4
    r2 = requests.post(f"{VOICEVOX}/synthesis",
                       params={"speaker": SPEAKER_ID},
                       json=query, headers={"Content-Type": "application/json"})
    r2.raise_for_status()
    with open(path, "wb") as f:
        f.write(r2.content)
    # 実際の長さを返す
    with wave.open(path) as wf:
        return wf.getnframes() / wf.getframerate()

# ── フレーム描画 ─────────────────────────────────────────────
def draw_frame(scene: dict, t: float, total: float) -> Image.Image:
    img = Image.new("RGB", (W, H), (0, 0, 0))
    draw = ImageDraw.Draw(img)
    r, g, b = scene["color"]
    progress = t / max(total, 0.001)

    # 背景グラデーション（暗い赤〜黒）
    for y in range(H):
        ratio = y / H
        br = int(r * 0.25 * (1 - ratio * 0.8))
        bg = int(g * 0.05 * (1 - ratio))
        bb = int(b * 0.05 * (1 - ratio))
        draw.line([(0, y), (W, y)], fill=(br, bg, bb))

    # ランダム稲妻ライン
    random.seed(int(t * 8))
    for _ in range(random.randint(1, 4)):
        x = random.randint(0, W)
        y0 = 0
        pts = [(x, y0)]
        while y0 < H:
            y0 += random.randint(30, 120)
            x  += random.randint(-80, 80)
            pts.append((x, y0))
        alpha = random.randint(60, 180)
        lc = (min(255, r + 80), min(255, g + 40), min(255, b + 40))
        if len(pts) > 1:
            draw.line(pts, fill=lc, width=random.randint(1, 3))

    # 横ライン（スキャンライン風）
    for y in range(0, H, 8):
        if random.random() < 0.15:
            draw.line([(0, y), (W, y)], fill=(r, g, b, 30), width=1)

    # メインテキスト（フェードイン）
    fade = min(1.0, t / 0.5)
    font_size = 100 if len(scene["text"]) <= 6 else 80
    try:
        font_main = ImageFont.truetype(FONT_PATH, font_size)
        font_sub  = ImageFont.truetype(FONT_PATH, 36)
        font_num  = ImageFont.truetype(FONT_PATH, 28)
    except Exception:
        font_main = ImageFont.load_default()
        font_sub  = font_main
        font_num  = font_main

    # メインテキスト
    lines = scene["text"].split("\n")
    total_h = len(lines) * (font_size + 20)
    y_start = H // 2 - total_h // 2 - 60
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font_main)
        tw = bbox[2] - bbox[0]
        x = (W - tw) // 2
        y = y_start + i * (font_size + 20)
        # 影
        for dx, dy in [(-3,3),(3,3),(-3,-3),(3,-3),(0,4)]:
            draw.text((x+dx, y+dy), line, font=font_main,
                      fill=(max(0,r-100), 0, 0))
        # 本文（グロー）
        text_color = (
            min(255, int(255 * fade)),
            min(255, int(fade * 40)),
            min(255, int(fade * 20)),
        )
        draw.text((x, y), line, font=font_main, fill=text_color)

    # サブタイトル
    bbox_s = draw.textbbox((0,0), scene["sub"], font=font_sub)
    sw = bbox_s[2] - bbox_s[0]
    sub_color = (min(255, int(200*fade)), min(255, int(200*fade)), min(255, int(200*fade)))
    draw.text(((W-sw)//2, H//2 + 120), scene["sub"], font=font_sub, fill=sub_color)

    # プログレスバー（下部）
    bar_y = H - 80
    bar_w = int(W * progress)
    draw.rectangle([(0, bar_y), (W, bar_y+6)], fill=(40, 0, 0))
    draw.rectangle([(0, bar_y), (bar_w, bar_y+6)], fill=(r, g//2, b//2))

    # 上部ロゴ
    draw.text((30, 40), "🎸 METAL FACTORY", font=font_num,
              fill=(180, 30, 30))

    # ブラーで発光感
    if int(t * 4) % 2 == 0:
        glow = img.filter(ImageFilter.GaussianBlur(radius=2))
        img = Image.blend(img, glow, 0.15)

    return img

# ── メイン生成 ───────────────────────────────────────────────
def main():
    print("🎸 ヘビーメタル ショート動画 生成開始")
    print(f"   解像度: {W}x{H}  FPS:{FPS}  話者: 青山龍星・熱血")

    audio_files  = []
    scene_frames = []
    total_frames = 0

    # 1. TTS生成 + フレーム数計算
    for i, scene in enumerate(SCENES):
        apath = f"{OUT_DIR}/audio_{i:02d}.wav"
        print(f"  🎙️  シーン{i+1}: '{scene['text'][:10]}...' → TTS生成中")
        actual_dur = tts(scene["text"], apath)
        # sceneの長さをTTS実長 + 少し余裕
        dur = max(scene["dur"], actual_dur + 0.3)
        scene["actual_dur"] = dur
        audio_files.append(apath)
        n = int(dur * FPS)
        scene_frames.append(n)
        total_frames += n
        print(f"     音声: {actual_dur:.1f}秒 → {dur:.1f}秒, {n}フレーム")

    total_dur = sum(s["actual_dur"] for s in SCENES)
    print(f"\n  📽️  総フレーム数: {total_frames} ({total_dur:.1f}秒)")

    # 2. フレーム画像生成
    frames_dir = f"{OUT_DIR}/frames"
    os.makedirs(frames_dir, exist_ok=True)
    frame_idx = 0
    for si, (scene, nf) in enumerate(zip(SCENES, scene_frames)):
        print(f"  🖼️  シーン{si+1} フレーム生成: {nf}枚")
        for fi in range(nf):
            t = fi / FPS
            img = draw_frame(scene, t, scene["actual_dur"])
            img.save(f"{frames_dir}/frame_{frame_idx:05d}.png")
            frame_idx += 1

    # 3. 音声結合
    print("  🔊 音声ファイル結合中...")
    concat_list = f"{OUT_DIR}/concat_audio.txt"
    with open(concat_list, "w") as f:
        for ap in audio_files:
            f.write(f"file '{ap}'\n")
    merged_audio = f"{OUT_DIR}/merged_audio.wav"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", concat_list, "-ar", "44100", merged_audio
    ], check=True, capture_output=True)

    # 4. FFmpeg で動画合成
    print("  🎬 FFmpeg で動画合成中...")
    out_mp4 = f"{OUT_DIR}/metal_short_sample.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", f"{frames_dir}/frame_%05d.png",
        "-i", merged_audio,
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        out_mp4
    ], check=True, capture_output=True)

    # 5. 後片付け
    shutil.rmtree(frames_dir)
    for ap in audio_files:
        os.remove(ap)
    os.remove(concat_list)
    os.remove(merged_audio)

    size_mb = os.path.getsize(out_mp4) / 1024 / 1024
    print(f"\n✅ 完成: {out_mp4}")
    print(f"   サイズ: {size_mb:.1f} MB  長さ: {total_dur:.1f}秒")
    print(f"   http://localhost:8088/apps/video_factory/output/metal_short_sample.mp4")

if __name__ == "__main__":
    main()
