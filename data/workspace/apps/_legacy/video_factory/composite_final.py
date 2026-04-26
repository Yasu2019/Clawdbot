#!/usr/bin/env python3
"""
A案 最終合成: Wav2Lip口パクキャラ + メタルMV背景 → 9:16動画
"""
import os, subprocess, math, random, wave
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT_DIR   = "/home/node/clawd/apps/video_factory/output"
FONT_PATH = "/usr/share/fonts/opentype/ipaexfont-gothic/ipaexg.ttf"
W, H      = 1080, 1920
FPS       = 25
CHAR_W    = 540   # キャラの表示サイズ

lipsync_vid = f"{OUT_DIR}/metal_lipsync.mp4"
audio_src   = f"{OUT_DIR}/wav2lip_audio.wav"
frames_dir  = f"{OUT_DIR}/frames_composite"
final_out   = f"{OUT_DIR}/metal_anime_final.mp4"

os.makedirs(frames_dir, exist_ok=True)

# 1. lipsync動画からフレームを展開
print("📤 口パクフレーム展開中...")
char_frames_dir = f"{OUT_DIR}/char_frames"
os.makedirs(char_frames_dir, exist_ok=True)
subprocess.run([
    "ffmpeg", "-y", "-i", lipsync_vid,
    "-r", str(FPS), f"{char_frames_dir}/cf_%05d.png"
], check=True, capture_output=True)

char_files = sorted(f for f in os.listdir(char_frames_dir) if f.endswith(".png"))
total_frames = len(char_files)
print(f"   キャラフレーム数: {total_frames}")

# 2. 音声の長さ取得
with wave.open(audio_src) as wf:
    dur = wf.getnframes() / wf.getframerate()

# 3. 合成フレーム生成
print("🎨 背景＋キャラ合成中...")

try:
    fmain = ImageFont.truetype(FONT_PATH, 72)
    fsub  = ImageFont.truetype(FONT_PATH, 32)
    flogo = ImageFont.truetype(FONT_PATH, 26)
except Exception:
    fmain = ImageFont.load_default()
    fsub = fmain
    flogo = fmain

LYRICS = [
    ("烈火の魂よ",      "SOUL OF RAGING FIRE",    0.0, 2.5),
    ("激情の若者よ",    "SCREAM AT THE WORLD",     2.5, 5.0),
    ("世界に叫べ",      "",                        5.0, 6.5),
    ("恐れるな",        "FEAR NOTHING",            6.5, 8.0),
    ("前に進め",        "",                        8.0, 9.5),
    ("鋼の意志で",      "TEAR THROUGH DARKNESS",   9.5, 12.0),
]

def get_lyric(t):
    for jp, en, t0, t1 in LYRICS:
        if t0 <= t < t1:
            return jp, en
    return "", ""

beat_bpm = 160
beat_ps  = beat_bpm / 60.0

for fi in range(total_frames):
    t          = fi / FPS
    beat_phase = t * beat_ps * math.pi * 2
    progress   = t / dur

    # ── 背景 ─────────────────────────────────────────────────
    bg = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    bd = ImageDraw.Draw(bg)

    # グラデーション背景
    r0 = 180 + int(40 * math.sin(beat_phase))
    for y in range(0, H, 2):
        ratio = y / H
        br = int(r0 * 0.25 * (1 - ratio * 0.9))
        bd.line([(0, y), (W, y)], fill=(br, 0, 0))

    # スポットライト
    beam_layer = Image.new("RGBA", (W, H), (0,0,0,0))
    bld = ImageDraw.Draw(beam_layer)
    for i in range(5):
        angle = -60 + i*30 + math.sin(t*0.7+i)*12
        bx = W//2 + int(math.sin(math.radians(angle))*3000)
        by = H//2 + int(math.cos(math.radians(angle))*3000)
        al = int(15 + 8 * math.sin(t*2+i*1.3))
        bld.polygon([(W//2-25, 0),(W//2+25, 0),(bx+50,by),(bx-50,by)],
                    fill=(r0, 20, 0, al))
    bg = Image.alpha_composite(bg, beam_layer)

    # 稲妻
    random.seed(int(t*10))
    lz = Image.new("RGBA", (W, H), (0,0,0,0))
    ld = ImageDraw.Draw(lz)
    for _ in range(random.randint(1,4)):
        lx, ly = random.randint(0, W), 0
        pts = [(lx, ly)]
        while ly < H*0.5:
            ly += random.randint(20,80)
            lx += random.randint(-60,60)
            pts.append((lx,ly))
        ld.line(pts, fill=(255,200,100,random.randint(60,180)),
                width=random.randint(1,3))
    bg = Image.alpha_composite(bg, lz)

    # 炎（下部）
    fl = Image.new("RGBA", (W, H), (0,0,0,0))
    fd = ImageDraw.Draw(fl)
    random.seed(int(t*20) + 9999)
    for _ in range(80):
        bx = random.uniform(0, W)
        by = random.uniform(H*0.85, H)
        bs = random.randint(4, 24)
        col = (min(255,r0+random.randint(-20,20)),
               random.randint(0,100), 0,
               random.randint(80,200))
        fd.ellipse([bx-bs,by-bs,bx+bs,by+bs], fill=col)
    bg = Image.alpha_composite(bg, fl)

    # ── キャラクター貼り付け ──────────────────────────────────
    cf_path = f"{char_frames_dir}/cf_{min(fi+1, total_frames):05d}.png"
    if os.path.exists(cf_path):
        char_img = Image.open(cf_path).convert("RGBA")
        # リサイズ（キャラを中央下寄せ）
        ratio = CHAR_W / char_img.width
        char_h = int(char_img.height * ratio)
        char_img = char_img.resize((CHAR_W, char_h), Image.LANCZOS)

        # ビート連動でわずかに揺れる
        shake_x = int(4 * math.sin(beat_phase * 2))
        cx_pos  = (W - CHAR_W) // 2 + shake_x
        cy_pos  = H - char_h - 180  # 下から180px上

        # キャラのシルエットをグロー
        glow = char_img.filter(ImageFilter.GaussianBlur(radius=12))
        glow_rgba = Image.new("RGBA", (W, H), (0,0,0,0))
        glow_rgba.paste(glow, (cx_pos, cy_pos), glow)
        bg = Image.alpha_composite(bg, glow_rgba)

        # キャラ本体
        char_layer = Image.new("RGBA", (W, H), (0,0,0,0))
        char_layer.paste(char_img, (cx_pos, cy_pos), char_img)
        bg = Image.alpha_composite(bg, char_layer)

    # ── UI レイヤー ──────────────────────────────────────────
    ui = Image.new("RGBA", (W, H), (0,0,0,0))
    ud = ImageDraw.Draw(ui)

    # 歌詞テロップ
    jp_text, en_text = get_lyric(t)
    if jp_text:
        bb = ud.textbbox((0,0), jp_text, font=fmain)
        tw = bb[2]-bb[0]
        tx = (W-tw)//2
        ty = H - 380
        for dx,dy in [(-3,3),(3,3),(0,3),(-3,-3),(3,-3)]:
            ud.text((tx+dx,ty+dy), jp_text, font=fmain,
                    fill=(120,0,0,200))
        ud.text((tx, ty), jp_text, font=fmain,
                fill=(255, int(200*abs(math.sin(beat_phase))), 20, 240))
    if en_text:
        bb_e = ud.textbbox((0,0), en_text, font=fsub)
        ew = bb_e[2]-bb_e[0]
        ud.text(((W-ew)//2, H-310), en_text, font=fsub,
                fill=(200,200,200,180))

    # 波形バー
    for bi in range(28):
        bh = int((0.3+0.7*abs(math.sin(beat_phase+bi*0.45)))*100)
        bx1 = bi*(W//28)+2
        bx2 = bx1+(W//28)-4
        ud.rectangle([(bx1, H-80-bh),(bx2, H-80)],
                     fill=(r0, 40, 0, 180))

    # プログレス
    ud.rectangle([(0,H-18),(W,H)], fill=(30,0,0,200))
    ud.rectangle([(0,H-18),(int(W*progress),H)], fill=(r0,50,0,255))

    # ロゴ
    ud.text((30,40), "🎸 METAL ANIME", font=flogo, fill=(200,30,30,230))
    ud.text((30,68), "青山龍星・熱血 × Wav2Lip", font=flogo, fill=(120,120,120,200))

    bg = Image.alpha_composite(bg, ui)

    bg.convert("RGB").save(f"{frames_dir}/frame_{fi:05d}.png")
    if fi % 25 == 0:
        print(f"   {fi}/{total_frames} ({t:.1f}s)")

# 4. FFmpeg合成
print("🎬 FFmpeg最終合成中...")
subprocess.run([
    "ffmpeg", "-y",
    "-framerate", str(FPS),
    "-i", f"{frames_dir}/frame_%05d.png",
    "-i", audio_src,
    "-c:v", "libx264", "-preset", "fast", "-crf", "18",
    "-c:a", "aac", "-b:a", "192k",
    "-pix_fmt", "yuv420p", "-shortest",
    final_out
], check=True, capture_output=True)

import shutil
shutil.rmtree(frames_dir)
shutil.rmtree(char_frames_dir)

size_mb = os.path.getsize(final_out)/1024/1024
print(f"\n✅ 完成: {final_out}")
print(f"   {size_mb:.1f}MB / {dur:.1f}秒 / {W}x{H}")
