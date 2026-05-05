# 02 動画処理パイプライン

## 入力
- mp4, mov, mkv
- 推奨: 1920x1080以下、30fps以下
- 1時間動画は5〜10分チャンクに分割

## 重要フレーム抽出
基準:
- 画面遷移が大きい
- UI要素が変化した
- 入力フォームや確認ダイアログが出た
- メニュー/設定画面が出た
- エラー/警告/完了画面が出た

## OCR
候補:
- Windows環境: PaddleOCR, Tesseract
- Docker環境: tesseract-ocr + 日本語言語データ
- 画面UI: OCR + 画像ファイル名 + 時刻情報をセットで保存

## 出力JSON例
```json
{
  "video": "input.mp4",
  "chunk": "chunk_001",
  "start_sec": 0,
  "end_sec": 300,
  "frames": [
    {
      "time_sec": 12.4,
      "image": "frames/chunk_001_0001.jpg",
      "ocr_text": "ログイン 送信 キャンセル",
      "change_score": 0.82,
      "candidate_action": "ログイン画面が表示された"
    }
  ]
}
```

## AIに渡す情報
- 画像パス
- OCRテキスト
- 時刻
- 前後差分説明
- ユーザーが補足した業務名
- 出力形式テンプレート
