# VOLUME RESTRICTIONS

## 悪い例
- /:/host
- C:\\Users 全体マウント
- ブラウザのユーザープロファイル共有
- .ssh ディレクトリ共有

## 良い例
- ./sandbox:/sandbox:rw
- ./logs:/logs:rw
- ./knowledge:/knowledge:ro
- ./input:/input:ro
