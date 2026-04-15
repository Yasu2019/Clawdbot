#!/usr/bin/env python3
"""
BGM生成: ヘビーメタル風サウンドをnumpyで合成
ディストーションギター + バス + ドラム（キック・スネア・ハット）
"""
import numpy as np
import wave, struct, os

SR  = 44100   # サンプリングレート
OUT = "/home/node/clawd/apps/video_factory/output/metal_bgm.wav"

def save_wav(path, data, sr=SR):
    data = np.clip(data, -1.0, 1.0)
    pcm  = (data * 32767).astype(np.int16)
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())

def tone(freq, dur, sr=SR, shape='saw'):
    t = np.linspace(0, dur, int(sr * dur), endpoint=False)
    if shape == 'saw':
        return 2 * (t * freq % 1) - 1
    elif shape == 'square':
        return np.sign(np.sin(2 * np.pi * freq * t))
    else:
        return np.sin(2 * np.pi * freq * t)

def distort(sig, drive=8.0, mix=0.85):
    """ギタードライブ: ソフトクリッピング"""
    driven = np.tanh(sig * drive) / np.tanh(drive)
    return sig * (1 - mix) + driven * mix

def adsr(sig, sr, attack=0.005, decay=0.05, sustain=0.7, release=0.1):
    n = len(sig)
    env = np.ones(n)
    a = int(sr * attack)
    d = int(sr * decay)
    r = int(sr * release)
    env[:a]    = np.linspace(0, 1, a)
    env[a:a+d] = np.linspace(1, sustain, d)
    if n > r:
        env[-r:] = np.linspace(sustain, 0, r)
    return sig * env

def kick(dur=0.35, sr=SR):
    """キックドラム: 周波数スウィープ + 低音"""
    t   = np.linspace(0, dur, int(sr * dur))
    env = np.exp(-t * 18)
    f   = 180 * np.exp(-t * 35) + 45
    sig = np.sin(2 * np.pi * np.cumsum(f) / sr) * env
    sig += np.random.randn(len(sig)) * 0.05 * env
    return sig * 0.9

def snare(dur=0.2, sr=SR):
    """スネア: ノイズ + 胴鳴り"""
    t    = np.linspace(0, dur, int(sr * dur))
    env  = np.exp(-t * 20)
    noise= np.random.randn(len(t)) * env
    body = np.sin(2 * np.pi * 200 * t) * np.exp(-t * 30)
    return (noise * 0.7 + body * 0.3) * 0.6

def hihat(dur=0.08, sr=SR, open_hat=False):
    """ハイハット"""
    t   = np.linspace(0, dur if not open_hat else 0.25,
                      int(sr * (dur if not open_hat else 0.25)))
    env = np.exp(-t * (15 if not open_hat else 5))
    sig = np.random.randn(len(t))
    # ハイパスフィルタ（差分で近似）
    sig = np.diff(np.concatenate([[0], sig]))
    return sig * env * 0.35

def power_chord(root_hz, dur, sr=SR):
    """パワーコード: ルート + 5度 + オクターブ"""
    fifth   = root_hz * 1.5
    octave  = root_hz * 2.0
    t       = np.linspace(0, dur, int(sr * dur))
    sig     = (tone(root_hz,  dur) * 0.5 +
               tone(fifth,    dur) * 0.3 +
               tone(octave,   dur) * 0.2)
    sig     = distort(sig, drive=12.0)
    # ローパス（倍音を少し落として太くする）
    from numpy.fft import rfft, irfft
    F = rfft(sig)
    freqs = np.fft.rfftfreq(len(sig), 1/sr)
    F[freqs > 4000] *= 0.3
    sig = irfft(F, len(sig))
    return adsr(sig, sr, attack=0.01, decay=0.08, sustain=0.75, release=0.15)

# ── コード進行 (Em - C - G - D パワーコード、BPM=160) ─────────
BPM       = 160
BEAT      = 60 / BPM
MEASURE   = BEAT * 4
DURATION  = 32.0   # 約32秒

# コード: E5 C5 G5 D5（ヘビーメタル定番進行）
CHORDS = [
    (82.4,  MEASURE),   # E2
    (65.4,  MEASURE),   # C2
    (98.0,  MEASURE),   # G2
    (73.4,  MEASURE),   # D2
]

print("🎸 BGM合成中...")

# ── ギタートラック ────────────────────────────────────────────
guitar = np.zeros(int(SR * DURATION))
t = 0.0
while t < DURATION:
    for freq, dur in CHORDS:
        if t >= DURATION:
            break
        chunk = power_chord(freq, min(dur, DURATION - t))
        start = int(t * SR)
        end   = start + len(chunk)
        if end <= len(guitar):
            guitar[start:end] += chunk * 0.55
        t += dur

# ── バストラック ──────────────────────────────────────────────
bass = np.zeros(int(SR * DURATION))
t = 0.0
while t < DURATION:
    for freq, dur in CHORDS:
        if t >= DURATION:
            break
        bass_freq = freq / 2  # 1オクターブ下
        chunk = tone(bass_freq, min(dur, DURATION - t), shape='saw')
        chunk = adsr(chunk, SR, attack=0.02, sustain=0.8, release=0.1)
        chunk = distort(chunk, drive=4.0)
        start = int(t * SR)
        end   = start + len(chunk)
        if end <= len(bass):
            bass[start:end] += chunk * 0.30
        t += dur

# ── ドラムトラック ────────────────────────────────────────────
drums = np.zeros(int(SR * DURATION))

def place(track, sig, t_sec):
    s = int(t_sec * SR)
    e = s + len(sig)
    if e <= len(track):
        track[s:e] += sig

t = 0.0
while t < DURATION:
    # キック: ビート1,3
    place(drums, kick(), t)
    place(drums, kick(), t + BEAT * 2)
    # スネア: ビート2,4
    place(drums, snare(), t + BEAT)
    place(drums, snare(), t + BEAT * 3)
    # ハイハット: 8分音符
    for i in range(8):
        place(drums, hihat(open_hat=(i%4==3)), t + BEAT * i * 0.5)
    # ダブルキック（メタルらしく）
    place(drums, kick(0.2) * 0.7, t + BEAT * 0.5)
    place(drums, kick(0.2) * 0.7, t + BEAT * 2.5)
    t += MEASURE

# ── ミックス & 書き出し ───────────────────────────────────────
mix = guitar + bass + drums
# 全体をノーマライズ
peak = np.max(np.abs(mix))
if peak > 0:
    mix = mix / peak * 0.82

# フェードイン・フェードアウト
fade = int(SR * 0.5)
mix[:fade] *= np.linspace(0, 1, fade)
mix[-fade:] *= np.linspace(1, 0, fade)

save_wav(OUT, mix)
dur_actual = len(mix) / SR
size_kb = os.path.getsize(OUT) // 1024
print(f"✅ BGM完成: {OUT}")
print(f"   {dur_actual:.1f}秒 / {size_kb}KB / {BPM}BPM")
