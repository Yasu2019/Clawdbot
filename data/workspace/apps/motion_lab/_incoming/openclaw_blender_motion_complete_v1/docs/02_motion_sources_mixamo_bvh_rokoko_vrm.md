# 02 モーションソース統合方針

## Mixamo
用途：歩行、走行、待機、ジェスチャー、会話動作、感情表現の土台。

推奨運用：
1. キャラクターまたは標準ダミーをMixamoにアップロード
2. 台本の動作タグに合うモーションを検索
3. FBXでダウンロード
4. Blenderでインポート
5. 対象キャラへリターゲット
6. NLAトラック化してシーンに組み込む

推奨タグ例：
- walk, idle, talking, pointing, looking around, sitting, stand up, pick up, turn, angry, surprised, happy

## BVHライブラリ
用途：研究用・無料配布モーションの大量活用。歩行、日常動作、腕振り、ジェスチャーなど。

代表例：
- CMU Graphics Lab Motion Capture Database
- ACCAD Motion Capture
- HDM05系データ
- その他無料BVH配布サイト

注意：
- ライセンスを必ず確認
- BVH骨格名がモデルと合わないため、ボーンマッピングが必要
- fps、スケール、座標軸を正規化する

## Rokoko Studio / Rokoko Motion Library
用途：自然な人物動作やモーションキャプチャ風の素材。

推奨：
- 無料枠で使えるモーションをFBX/BVH出力
- Blenderへ取り込み
- Rokoko Retargeting Add-onを検討

## VRMキャラクター
用途：日本語圏で扱いやすい人型キャラ。

推奨：
- VRM Add-on for Blenderで読み込み
- Humanoidボーン構造確認
- Mixamo/BVHからRigify/VRMへリターゲット

## 優先順位
1. 台本に一致するMixamoモーション
2. 近いBVHモーション
3. Rokoko系モーション
4. AI生成補助キーフレーム
5. 手修正
