# Remotion連携メモ

1. `templates/iatf_training_script.md` で原稿を作成
2. `/tts/speak` に `purpose=iatf_training` で音声生成
3. 生成音声と字幕をRemotionプロジェクトに配置
4. IATF教育動画としてMP4出力

実装方針:
- `narration.json` に字幕タイムラインを保存
- 音声ファイル名と原稿ハッシュを紐づけ
- 動画版数、原稿版数、承認者をメタデータ保存
