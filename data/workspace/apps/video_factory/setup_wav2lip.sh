#!/bin/bash
# A案: Wav2Lip セットアップスクリプト
# gateway コンテナ内で実行: bash /home/node/clawd/apps/video_factory/setup_wav2lip.sh

set -e
W2L_DIR="/home/node/clawd/apps/video_factory/wav2lip"
mkdir -p "$W2L_DIR/checkpoints"
cd "$W2L_DIR"

echo "=== 1. Wav2Lip リポジトリ取得 ==="
if [ ! -d "repo" ]; then
  git clone https://github.com/Rudrabha/Wav2Lip.git repo
fi

echo "=== 2. 依存パッケージ ==="
pip3 install -q librosa==0.9.2 numba==0.56.4 basicsr facexlib gfpgan 2>&1 | tail -5

echo "=== 3. モデルウェイト確認 ==="
MODEL_URL="https://iiitaphyd-my.sharepoint.com/:u:/g/personal/radrabha_m_research_iiit_ac_in/Eb3LEzbfuKlJiR600lQWRxgBIY27JZg80f7V9ztEs67rRQ?e=TBYD1k"
FACE_URL="https://www.adrianbulat.com/downloads/python-fan/s3fd-619a316812.pth"

echo "  モデルURL (手動DL必要):"
echo "  Wav2Lip.pth → $W2L_DIR/checkpoints/wav2lip.pth"
echo "  Face detection → $W2L_DIR/checkpoints/s3fd.pth"
echo ""
echo "  ※ SharePointリンクのため自動DLは困難です。"
echo "     代替: wav2lip_gan.pth を huggingface からDL"

# HuggingFaceから取得を試みる
pip3 install -q huggingface_hub 2>/dev/null
python3 -c "
from huggingface_hub import hf_hub_download
import shutil, os

dest = '$W2L_DIR/checkpoints'
try:
    p = hf_hub_download(repo_id='numz/wav2lip_studio', filename='Wav2Lip/wav2lip_gan.pth',
                        local_dir='/tmp/w2l_dl')
    shutil.copy(p, os.path.join(dest, 'wav2lip_gan.pth'))
    print('✅ wav2lip_gan.pth DL完了')
except Exception as e:
    print(f'⚠️  HuggingFace DL失敗: {e}')
    print('   手動でモデルを配置してください')

# face detection model
import urllib.request
fd_path = os.path.join(dest, 's3fd.pth')
if not os.path.exists(fd_path):
    try:
        print('  face detection model DL中...')
        urllib.request.urlretrieve(
            'https://www.adrianbulat.com/downloads/python-fan/s3fd-619a316812.pth',
            fd_path)
        print('✅ s3fd.pth DL完了')
    except Exception as e2:
        print(f'⚠️  face detection DL失敗: {e2}')
"

echo ""
echo "=== セットアップ完了確認 ==="
ls -lh "$W2L_DIR/checkpoints/"
