# 04 運用Runbook

## 毎日
- Langfuseで失敗探索を確認
- evidence_idなし回答を抽出
- 「不明」と回答した質問を改善候補にする

## 毎週
- IATF・QC・図面ツリーの人間確認済み率を確認
- よく使う質問を評価セットへ登録
- 誤回答を defect_knowledge に蓄積

## 毎月
- Qdrant検索だけで回答したケースとCorpus探索ケースを比較
- トークン使用量を比較
- 根拠提示率を確認
- 古い文書をdeprecated扱いにする

## 異常時
### 回答が断定しすぎる
- C2S_REQUIRE_EVIDENCE=trueを確認
- required_evidence_countを増やす
- domain_rules.yamlのmust_not_guessを追加

### 図面datumを間違える
- human_verify_fieldsにdatum関連を追加
- 図面PDFとSTEP候補を別ノードに分離
- 「推定」「確認済み」の表示を分ける

### API消費が多い
- C2S_CLOUD_FALLBACK=false
- ローカルLLMでroot/branchだけ先に生成
- leaf生成は必要時だけにする

