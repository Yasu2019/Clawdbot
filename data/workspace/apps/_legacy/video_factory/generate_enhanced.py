#!/usr/bin/env python3
"""
AI Video Factory - C案強化版: ライブメタルMV風
炎パーティクル・スポットライト・インパクトテキスト・波形バー
"""
import os, json, requests, subprocess, wave, shutil, math, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

OUT_DIR    = "/home/node/clawd/apps/video_factory/output"
FONT_PATH  = "/usr/share/fonts/opentype/ipaexfont-gothic/ipaexg.ttf"
VOICEVOX   = "http://voicevox:50021"
SPEAKER_ID = 81
W, H       = 1080, 1920
FPS        = 24
os.makedirs(OUT_DIR, exist_ok=True)

SCENES = [
    {"text": "烈火の魂",              "sub": "SOUL OF RAGING FIRE",    "dur": 3.0,  "hue": (255,30,0)},
    {"text": "激情の若者よ\n世界に叫べ", "sub": "SCREAM AT THE WORLD",   "dur": 5.5,  "hue": (220,20,20)},
    {"text": "恐れるな\n前に進め",      "sub": "FEAR NOTHING",           "dur": 5.5,  "hue": (255,70,0)},
    {"text": "鋼の意志で\n闇を切り裂け", "sub": "TEAR THROUGH DARKNESS",  "dur": 6.0,  "hue": (200,10,50)},
    {"text": "烈火よ燃えろ\n魂の限り",  "sub": "BURN WITH ALL YOUR SOUL", "dur": 6.0,  "hue": (255,40,0)},
    {"text": "限界を超えろ\nお前は最強だ","sub": "SURPASS YOUR LIMITS",   "dur": 5.0,  "hue": (220,0,0)},
]

# ── パーティクルクラス ────────────────────────────────────────
class FireParticle:
    def __init__(self, w, h):
        self.reset(w, h)

    def reset(self, w, h):
        self.x   = random.uniform(0, w)
        self.y   = random.uniform(h * 0.7, h)
        self.vx  = random.uniform(-1.5, 1.5)
        self.vy  = random.uniform(-6, -2)
        self.life= random.uniform(0.4, 1.0)
        self.age = 0.0
        self.size= random.randint(4, 14)

    def update(self, dt):
        self.x   += self.vx
        self.vy  *= 0.97
        self.vx  *= 0.99
        self.y   += self.vy
        self.age += dt
        self.life -= dt * random.uniform(0.4, 0.8)

    @property
    def alive(self):
        return self.life > 0

    def color(self):
        r = min(255, int(255 * min(1.0, self.life * 2)))
        g = min(255, int(180 * self.life * self.life))
        b = 0
        return (r, g, b, int(180 * self.life))


def tts(text, path):
    clean = text.replace("\n", "。")
    r = requests.post(f"{VOICEVOX}/audio_query",
                      params={"text": clean, "speaker": SPEAKER_ID})
    r.raise_for_status()
    q = r.json()
    q["speedScale"]      = 0.88
    q["pitchScale"]      = -0.06
    q["intonationScale"] = 1.6
    q["volumeScale"]     = 1.4
    r2 = requests.post(f"{VOICEVOX}/synthesis",
                       params={"speaker": SPEAKER_ID}, json=q,
                       headers={"Content-Type": "application/json"})
    r2.raise_for_status()
    with open(path, "wb") as f:
        f.write(r2.content)
    with wave.open(path) as wf:
        return wf.getnframes() / wf.getframerate()


def draw_frame(scene, t, total_dur, particles, beat_phase):
    r0, g0, b0 = scene["hue"]
    progress    = t / max(total_dur, 0.001)

    # ── ベース: 黒〜暗赤グラデーション ──────────────────────
    img  = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    base = ImageDraw.Draw(img)
    for y in range(0, H, 2):
        ratio = y / H
        br = int(r0 * 0.30 * (1 - ratio * 0.9))
        base.line([(0, y), (W, y)], fill=(br, 0, 0, 255))

    # ── スポットライトビーム ─────────────────────────────────
    beam_layer = Image.new("RGBA", (W, H), (0,0,0,0))
    bd = ImageDraw.Draw(beam_layer)
    num_beams = 5
    for i in range(num_beams):
        angle = -60 + i * 30 + math.sin(t * 0.7 + i) * 12
        bx    = W // 2 + int(math.sin(math.radians(angle)) * 3000)
        by    = H // 2 + int(math.cos(math.radians(angle)) * 3000)
        alpha = int(18 + 8 * math.sin(t * 2 + i * 1.3))
        bd.polygon([(W//2-30, 0), (W//2+30, 0), (bx+60, by), (bx-60, by)],
                   fill=(r0, g0//2, 0, alpha))
    img = Image.alpha_composite(img, beam_layer)

    # ── 炎パーティクル ────────────────────────────────────────
    fire_layer = Image.new("RGBA", (W, H), (0,0,0,0))
    fd = ImageDraw.Draw(fire_layer)
    for p in particles:
        if p.alive:
            c = p.color()
            s = max(1, int(p.size * p.life))
            fd.ellipse([p.x-s, p.y-s, p.x+s, p.y+s], fill=c)
    # ボトム炎帯（密度高め）
    for _ in range(60):
        bx = random.uniform(0, W)
        by = random.uniform(H*0.82, H)
        bs = random.randint(3, 22)
        al = random.randint(60, 200)
        col = (
            min(255, r0 + random.randint(-30, 30)),
            random.randint(0, 120),
            0, al
        )
        fd.ellipse([bx-bs, by-bs, bx+bs, by+bs], fill=col)
    img = Image.alpha_composite(img, fire_layer)

    # ── 稲妻 ─────────────────────────────────────────────────
    lz = Image.new("RGBA", (W, H), (0,0,0,0))
    ld = ImageDraw.Draw(lz)
    random.seed(int(t * 10))
    for _ in range(random.randint(2, 5)):
        lx, ly = random.randint(0, W), 0
        pts = [(lx, ly)]
        while ly < H * 0.6:
            ly += random.randint(20, 80)
            lx += random.randint(-60, 60)
            pts.append((lx, ly))
        al  = random.randint(80, 220)
        ld.line(pts, fill=(255, 200, 100, al), width=random.randint(1, 3))
    img = Image.alpha_composite(img, lz)

    # ── テキスト ──────────────────────────────────────────────
    txt_layer = Image.new("RGBA", (W, H), (0,0,0,0))
    td = ImageDraw.Draw(txt_layer)

    # フォント
    try:
        big   = int(90 + 8 * math.sin(beat_phase))
        fmain = ImageFont.truetype(FONT_PATH, big if len(scene["text"]) <= 6 else int(big*0.8))
        fsub  = ImageFont.truetype(FONT_PATH, 38)
        flogo = ImageFont.truetype(FONT_PATH, 28)
    except Exception:
        fmain = ImageFont.load_default()
        fsub  = fmain
        flogo = fmain

    # テキスト slam-in エフェクト（最初0.4秒でドロップイン）
    slam_t = min(1.0, t / 0.35)
    slam_y = int((1 - slam_t**0.4) * (-300))  # 上からドロップ

    lines  = scene["text"].split("\n")
    line_h = fmain.size + 18
    total_text_h = len(lines) * line_h
    y_center = H // 2 - total_text_h // 2 - 80 + slam_y

    # ビート連動の揺れ
    shake = int(6 * math.sin(beat_phase * 2))

    for i, line in enumerate(lines):
        bb = td.textbbox((0,0), line, font=fmain)
        tw = bb[2] - bb[0]
        tx = (W - tw)//2 + shake
        ty = y_center + i * line_h

        # 発光シャドウ（多重）
        for radius in [8, 5, 2]:
            for dx, dy in [(-radius,radius),(radius,radius),
                           (-radius,-radius),(radius,-radius),(0,radius)]:
                td.text((tx+dx, ty+dy), line, font=fmain,
                        fill=(min(255,r0+40), 0, 0, 160))

        # 本文（ビート連動で明滅）
        brightness = int(220 + 35 * math.sin(beat_phase))
        td.text((tx, ty), line, font=fmain,
                fill=(brightness, int(brightness*0.15), int(brightness*0.05), 255))

    # サブタイトル
    bb_s = td.textbbox((0,0), scene["sub"], font=fsub)
    sw   = bb_s[2] - bb_s[0]
    sub_alpha = int(200 * min(1.0, t / 0.6))
    td.text(((W-sw)//2 + shake, H//2 + 130 + slam_y), scene["sub"],
            font=fsub, fill=(200,200,200, sub_alpha))

    img = Image.alpha_composite(img, txt_layer)

    # ── 波形バー（下部）──────────────────────────────────────
    ui_layer = Image.new("RGBA", (W, H), (0,0,0,0))
    ud = ImageDraw.Draw(ui_layer)
    bar_count = 32
    bar_w     = W // bar_count
    for bi in range(bar_count):
        bh = int((0.3 + 0.7 * abs(math.sin(beat_phase + bi * 0.4 +
                  math.sin(t * 3 + bi * 0.2) * 0.5))) * 120)
        bx1 = bi * bar_w + 2
        bx2 = bx1 + bar_w - 4
        col = (
            min(255, r0),
            min(255, int(g0 + bh * 0.5)),
            0,
            int(180 + 60 * abs(math.sin(beat_phase + bi * 0.3)))
        )
        ud.rectangle([(bx1, H-80-bh), (bx2, H-80)], fill=col)

    # プログレスバー
    bary = H - 20
    ud.rectangle([(0, bary-4), (W, bary)], fill=(40,0,0,200))
    ud.rectangle([(0, bary-4), (int(W*progress), bary)], fill=(r0, 60, 0, 255))

    # ロゴ
    ud.text((30, 40), "🎸 METAL FACTORY", font=flogo, fill=(200, 30, 30, 230))
    ud.text((30, 72), "青山龍星・熱血 × VOICEVOX", font=flogo, fill=(120, 120, 120, 200))

    img = Image.alpha_composite(img, ui_layer)

    # ── シーン切り替えフラッシュ ─────────────────────────────
    if t < 0.08:
        fade_alpha = int(220 * (1 - t / 0.08))
        flash = Image.new("RGBA", (W, H), (r0, g0//3, 0, fade_alpha))
        img   = Image.alpha_composite(img, flash)

    # RGB変換
    return img.convert("RGB")


def main():
    print("🎸 C案強化版 - ライブメタルMV生成開始")

    audio_files  = []
    scene_durs   = []

    # 1. TTS
    for i, scene in enumerate(SCENES):
        apath = f"{OUT_DIR}/audio_{i:02d}.wav"
        print(f"  🎙️  シーン{i+1}: TTS生成中...")
        real_dur = tts(scene["text"], apath)
        dur      = max(scene["dur"], real_dur + 0.4)
        scene["actual_dur"] = dur
        audio_files.append(apath)
        scene_durs.append(dur)
        print(f"     {real_dur:.1f}秒 → {dur:.1f}秒")

    total_dur = sum(scene_durs)
    print(f"\n  📽️  総尺: {total_dur:.1f}秒")

    # 2. フレーム生成
    frames_dir = f"{OUT_DIR}/frames_enh"
    os.makedirs(frames_dir, exist_ok=True)

    # 炎パーティクル初期化
    particles = [FireParticle(W, H) for _ in range(120)]
    dt        = 1.0 / FPS

    frame_idx  = 0
    beat_bpm   = 160  # ヘビーメタルBPM
    beat_per_s = beat_bpm / 60.0

    for si, (scene, dur) in enumerate(zip(SCENES, scene_durs)):
        nf = int(dur * FPS)
        print(f"  🖼️  シーン{si+1} {nf}フレーム描画中...")
        for fi in range(nf):
            t          = fi / FPS
            beat_phase = (t * beat_per_s) * math.pi * 2

            # パーティクル更新
            for p in particles:
                p.update(dt)
                if not p.alive:
                    p.reset(W, H)

            img = draw_frame(scene, t, dur, particles, beat_phase)
            img.save(f"{frames_dir}/frame_{frame_idx:05d}.png")
            frame_idx += 1

    # 3. 音声結合
    print("  🔊 音声結合中...")
    clist = f"{OUT_DIR}/concat_enh.txt"
    with open(clist, "w") as f:
        for ap in audio_files:
            f.write(f"file '{ap}'\n")
    merged = f"{OUT_DIR}/merged_enh.wav"
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                    "-i", clist, "-ar", "44100", merged],
                   check=True, capture_output=True)

    # 4. 動画合成
    print("  🎬 FFmpeg合成中...")
    out_mp4 = f"{OUT_DIR}/metal_mv_enhanced.mp4"
    subprocess.run([
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", f"{frames_dir}/frame_%05d.png",
        "-i", merged,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-shortest", out_mp4
    ], check=True, capture_output=True)

    # 後片付け
    shutil.rmtree(frames_dir)
    for ap in audio_files:
        os.remove(ap)
    os.remove(clist)
    os.remove(merged)

    size_mb = os.path.getsize(out_mp4) / 1024 / 1024
    print(f"\n✅ 完成: {out_mp4}")
    print(f"   {size_mb:.1f} MB / {total_dur:.1f}秒")

if __name__ == "__main__":
    main()
