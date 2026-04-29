# TTSモデル選定ガイド

## 実務判断
- 速度最優先: StyleBertVITS2 / VOICEVOX
- 読み間違い低減: Gemini / Fish Audio
- 感情表現: しきさいどりTTS / MioTTS
- 完全ローカル: StyleBertVITS2 / GPT-SoVITS / VOICEVOX
- 顧客向け: Fish Audio / Gemini

## 現場QA向け推奨
1. 工場アラート: ローカルTTS固定。外部API停止時でも通知可能にする。
2. IATF教育動画: 原稿レビュー後にFish AudioまたはしきさいどりTTS。
3. 顧客向け: 読み上げ原稿、音声、字幕を保存し、監査証跡にする。
4. 試作・遊び: MioTTSなど表現力の高いモデルを使う。ただし正式資料では再確認。
