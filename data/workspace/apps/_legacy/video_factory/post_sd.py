import os, subprocess, sys, time

OUT = '/home/node/clawd/apps/video_factory/output'
LOG = f'{OUT}/sd_log.txt'

# SDキャラ画像確認
sd_img = f'{OUT}/character_sd.png'
if not os.path.exists(sd_img):
    print('SD画像がまだありません')
    sys.exit(1)

print('✅ SD画像確認。Wav2Lip + 合成を開始...')

# Wav2Lip
w2l_dir   = '/home/node/clawd/apps/video_factory/wav2lip'
audio_src = f'{OUT}/wav2lip_audio.wav'
face_vid  = f'{OUT}/face_sd_static.mp4'
lip_out   = f'{OUT}/sd_lipsync.mp4'

# 静止画→動画
import wave
with wave.open(audio_src) as wf:
    dur = wf.getnframes() / wf.getframerate()

subprocess.run(['ffmpeg','-y','-loop','1','-i',sd_img,
    '-t',str(dur+0.5),'-r','25',
    '-c:v','libx264','-pix_fmt','yuv420p', face_vid],
    check=True, capture_output=True)

# Wav2Lip推論
repo = f'{w2l_dir}/repo'
ckpt = f'{w2l_dir}/checkpoints/wav2lip_gan.pth'
env  = os.environ.copy()
env['PYTHONPATH'] = repo
subprocess.run([
    'python3', f'{repo}/inference.py',
    '--checkpoint_path', ckpt,
    '--face', face_vid,
    '--audio', audio_src,
    '--outfile', lip_out,
    '--pads', '0', '15', '0', '0',
    '--resize_factor', '1',
    '--nosmooth',
], check=True, env=env, cwd=repo, capture_output=True)

# 合成スクリプト呼び出し（composite用にパスを差し替え）
import importlib.util, types

# composite_finalを改変して実行
spec = importlib.util.spec_from_file_location('comp',
    '/home/node/clawd/apps/video_factory/composite_final.py')
# 直接FFmpegで合成
voice_tmp = f'{OUT}/voice_sd.wav'
subprocess.run(['ffmpeg','-y','-i',lip_out,'-vn','-acodec','pcm_s16le',voice_tmp],
    check=True, capture_output=True)

final = f'{OUT}/metal_sd_final.mp4'
subprocess.run([
    'ffmpeg','-y',
    '-i', f'{OUT}/metal_mv_bgm.mp4',  # 背景映像
    '-i', lip_out,                      # SDリップシンク
    '-i', audio_src,                    # 音声
    '-i', f'{OUT}/metal_bgm.wav',       # BGM
    '-filter_complex',
    '[1:v]scale=540:540[char];'
    '[0:v][char]overlay=(W-540)/2:(H-540)/2-180[vid];'
    '[2:a]volume=1.0[v];[3:a]volume=0.28[b];[v][b]amix=inputs=2:duration=shortest[aout]',
    '-map', '[vid]', '-map', '[aout]',
    '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
    '-c:a', 'aac', '-b:a', '192k',
    '-pix_fmt', 'yuv420p', '-shortest', final
], check=True, capture_output=True)

os.remove(voice_tmp)
os.remove(face_vid)

sz = os.path.getsize(final)/1024/1024
print(f'✅ SDキャラ最終動画完成: {final} ({sz:.1f}MB)')
