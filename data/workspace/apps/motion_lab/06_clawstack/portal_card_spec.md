# Clawstack Portalカード案

## カード名
Cinematic Mocap Studio

## 機能
- 台本貼り付け
- 動作表CSV生成
- カット単位タスク作成
- Blender用Python生成
- QCチェックリスト出力
- Codexレビュー用プロンプト出力

## 安全設計
- 元ファイルを直接上書きしない
- output/に日付付きで保存
- Blender実行前にdry-run
- 外部API利用は手動承認
- ローカルLLM優先
