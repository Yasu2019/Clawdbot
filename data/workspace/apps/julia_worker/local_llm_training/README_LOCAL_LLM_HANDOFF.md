# Local LLM Handoff

このフォルダは、Qwen / Gemma / DeepSeek等のローカルLLMへ渡すための教育用資料です。

## 教育ポイント

- JuliaはPython置換ではない
- 数値計算Workerとして使う
- 既存Clawstackを壊さない
- override compose方式
- Gitバックアップ必須
- 計算結果は簡易推定
- 正式判断はCAE/実測

## ローカルLLMに渡す短文

ClawstackにJuliaを追加するときは、既存構成を壊さず、Juliaを高速数値計算Workerとして追加する。
Pythonは司令塔、Juliaは計算部品、CAEソルバーは正式検証担当。
既存docker-compose.ymlを直接書き換えず、override composeで追加する。
Portalにはカードを追加するだけ。
Node-REDにはサンプルフローを追加するだけ。
必ずGitバックアップを取る。
