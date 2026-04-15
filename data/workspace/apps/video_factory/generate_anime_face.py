#!/usr/bin/env python3
"""
アニメ風18歳男性キャラクター画像生成（Pillow）
ヘビーメタル系 / 正面顔 / Wav2Lip用
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os, math

OUT = "/home/node/clawd/apps/video_factory/output/character_face.png"
W, H = 512, 512

def draw_character():
    img  = Image.new("RGBA", (W, H), (18, 18, 24, 255))
    draw = ImageDraw.Draw(img)

    cx, cy = W // 2, H // 2

    # ── 背景グロー ──────────────────────────────────────────
    for r in range(200, 0, -4):
        alpha = int(40 * (1 - r/200))
        draw.ellipse([cx-r, cy-r+30, cx+r, cy+r+30],
                     fill=(80, 0, 0, alpha))

    # ── 首 ──────────────────────────────────────────────────
    draw.rectangle([cx-35, cy+110, cx+35, cy+180],
                   fill=(210, 175, 150))

    # ── 顔輪郭（卵型）────────────────────────────────────────
    face_rect = [cx-110, cy-120, cx+110, cy+140]
    draw.ellipse(face_rect, fill=(220, 185, 158))  # 肌色

    # ── 頭部シルエット（上部を広げる）────────────────────────
    draw.ellipse([cx-115, cy-160, cx+115, cy+20],
                 fill=(220, 185, 158))

    # ── スパイキーヘア（メタル系 / 黒）──────────────────────
    hair_color   = (15, 10, 10)
    streak_color = (80, 0, 0)  # 赤いメッシュ

    # 前髪・サイドヘア
    hair_points = [
        # 左側スパイク群
        [(cx-130, cy-100), (cx-160, cy-200), (cx-100, cy-140)],
        [(cx-100, cy-140), (cx-140, cy-240), (cx-70,  cy-170)],
        [(cx-70,  cy-170), (cx-100, cy-270), (cx-30,  cy-180)],
        # 上部スパイク
        [(cx-30,  cy-180), (cx-50,  cy-300), (cx+10,  cy-190)],
        [(cx+10,  cy-190), (cx,     cy-310), (cx+50,  cy-185)],
        [(cx+50,  cy-185), (cx+60,  cy-290), (cx+90,  cy-175)],
        # 右側スパイク群
        [(cx+90,  cy-175), (cx+130, cy-260), (cx+110, cy-150)],
        [(cx+110, cy-150), (cx+155, cy-220), (cx+130, cy-110)],
    ]
    for pts in hair_points:
        draw.polygon(pts, fill=hair_color)

    # 赤メッシュ（数本）
    mesh_pts = [
        [(cx-15, cy-185), (cx-35, cy-300), (cx+5,  cy-190)],
        [(cx+60, cy-180), (cx+70, cy-295), (cx+95, cy-170)],
    ]
    for pts in mesh_pts:
        draw.polygon(pts, fill=streak_color)

    # 後頭部の黒塗り
    draw.ellipse([cx-120, cy-155, cx+120, cy-20], fill=hair_color)
    # 前髪のかかり
    draw.polygon([(cx-110, cy-120), (cx-90, cy-60), (cx-40, cy-140),
                  (cx-10, cy-70),   (cx+50, cy-130), (cx+100, cy-60),
                  (cx+110, cy-120)], fill=hair_color)

    # ── 眉毛（太め・つり上がり）──────────────────────────────
    brow_color = (20, 15, 15)
    # 左眉
    draw.polygon([(cx-85, cy-55), (cx-30, cy-70),
                  (cx-28, cy-60), (cx-83, cy-45)],
                 fill=brow_color)
    # 右眉
    draw.polygon([(cx+28, cy-70), (cx+83, cy-55),
                  (cx+81, cy-45), (cx+26, cy-60)],
                 fill=brow_color)

    # ── 目（シャープなアニメ目）──────────────────────────────
    eye_w, eye_h = 48, 30
    # 左目
    lx, ly = cx - 58, cy - 32
    draw.ellipse([lx-eye_w//2, ly-eye_h//2, lx+eye_w//2, ly+eye_h//2],
                 fill=(240, 240, 250))  # 白目
    draw.ellipse([lx-16, ly-14, lx+16, ly+14],
                 fill=(40, 20, 80))     # 虹彩（紫）
    draw.ellipse([lx-10, ly-10, lx+10, ly+10],
                 fill=(5, 5, 10))       # 瞳孔
    draw.ellipse([lx+2, ly-8, lx+8, ly-2],
                 fill=(255, 255, 255))  # ハイライト
    # アイライン
    draw.arc([lx-eye_w//2-2, ly-eye_h//2-2, lx+eye_w//2+2, ly+eye_h//2+2],
             200, 340, fill=(10,5,20), width=4)

    # 右目
    rx, ry = cx + 58, cy - 32
    draw.ellipse([rx-eye_w//2, ry-eye_h//2, rx+eye_w//2, ry+eye_h//2],
                 fill=(240, 240, 250))
    draw.ellipse([rx-16, ry-14, rx+16, ry+14], fill=(40, 20, 80))
    draw.ellipse([rx-10, ry-10, rx+10, ry+10], fill=(5, 5, 10))
    draw.ellipse([rx+2, ry-8, rx+8, ry-2], fill=(255, 255, 255))
    draw.arc([rx-eye_w//2-2, ry-eye_h//2-2, rx+eye_w//2+2, ry+eye_h//2+2],
             200, 340, fill=(10,5,20), width=4)

    # ── 鼻 ──────────────────────────────────────────────────
    draw.line([(cx, cy+10), (cx-10, cy+38)], fill=(190,155,130), width=2)
    draw.line([(cx, cy+10), (cx+10, cy+38)], fill=(190,155,130), width=2)
    draw.ellipse([cx-14, cy+32, cx-6, cy+40], fill=(190,150,125))
    draw.ellipse([cx+6,  cy+32, cx+14, cy+40], fill=(190,150,125))

    # ── 口（やや厳しい表情）──────────────────────────────────
    # 下唇
    draw.ellipse([cx-32, cy+58, cx+32, cy+78], fill=(185, 110, 100))
    # 上唇
    draw.polygon([(cx-32, cy+66), (cx-16, cy+56), (cx, cy+60),
                  (cx+16, cy+56), (cx+32, cy+66)],
                 fill=(165, 90, 82))
    # 口の線
    draw.line([(cx-32, cy+66), (cx+32, cy+66)], fill=(120, 60, 60), width=2)

    # ── ピアス（左耳）────────────────────────────────────────
    draw.ellipse([cx-118, cy+10, cx-108, cy+20], fill=(200, 180, 50))  # 金ピアス

    # ── 服（黒バンドTシャツ）─────────────────────────────────
    draw.rectangle([cx-160, cy+170, cx+160, H+10], fill=(15, 15, 20))
    # スカル風プリント（シンプル）
    skull_c = (60, 0, 0)
    draw.ellipse([cx-25, cy+185, cx+25, cy+225], fill=skull_c)
    draw.ellipse([cx-20, cy+218, cx+20, cy+235], fill=skull_c)
    draw.ellipse([cx-10, cy+230, cx-2,  cy+238], fill=(15,15,20))
    draw.ellipse([cx+2,  cy+230, cx+10, cy+238], fill=(15,15,20))

    # 最終調整：ソフトなブラー
    img = img.filter(ImageFilter.GaussianBlur(radius=0.6))
    img.save(OUT)
    print(f"✅ キャラクター画像生成完了: {OUT}")
    print(f"   {W}x{H}px")

if __name__ == "__main__":
    draw_character()
