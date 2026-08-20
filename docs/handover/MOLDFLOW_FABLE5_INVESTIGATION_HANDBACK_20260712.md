# Moldflow 調査引継ぎメモ

作成日: 2026-07-12 JST
引継ぎ先: Fable5

## 結論

現状の把握結果は次のとおりです。

1. Moldflow CAE Studio の実体は確認できた。
2. ただし、Moldflow 本体の計算精度を本当に上げる段階ではなく、まずは既存の proxy solver と橋渡し層の状態整理が必要。
3. 公式/商用の Moldflow 材料カード DB は、この作業領域では未導入。
4. 代わりに、一般材料の `engines/fea/materials.json` と、Materials Project の API 利用準備は存在する。
5. 既存の MCP ブリッジは read-only で、書き込み操作はまだ止められている。

## 確認した事実

### 1. Moldflow CAE Studio の実体

- アプリ本体は `[data/workspace/apps/moldflow_cae_studio](/D:/Clawdbot_Docker_20260125/data/workspace/apps/moldflow_cae_studio)` にある。
- 主要ファイルは `index.html` と `app.js`。
- API 実装は `[scripts/moldflow_cae_studio_api.py](/D:/Clawdbot_Docker_20260125/scripts/moldflow_cae_studio_api.py)`。
- コード上の `DEFAULT_PORT` は `8776`。
- 既存ハンドオフ文書では UI 8088 / API 8776 の記述があるが、今回の静的確認では API 側は 8776 を指していた。

### 2. 既存のハンドオフ文書

- STEP1 から STEP4 までの引継ぎ文書が `docs/handover/` にある。
- 特に STEP4 は Gate Advisor MVP までの到達点を記録している。
- 精度ロードマップは `[docs/moldflow_accuracy_l3_to_l10_te_plan.md](/D:/Clawdbot_Docker_20260125/docs/moldflow_accuracy_l3_to_l10_te_plan.md)` にある。

### 3. MCP / ブリッジ状態

- 調査対象のブリッジは `[data/workspace/moldflow_bridge/moldflow_mcp_server.py](/D:/Clawdbot_Docker_20260125/data/workspace/moldflow_bridge/moldflow_mcp_server.py)`。
- これは Synergy COM の read-only 検証用で、`analysis_enabled=false` のまま。
- 提供ツールは `moldflow_bridge_status`, `moldflow_probe_com`, `moldflow_inspect_state`, `moldflow_inspect_members`, `moldflow_readiness_gate` など。
- 書き込み系は `MOLDFLOW_ENABLE_WRITE_OPERATIONS=1` がないと止まる設計。

### 4. リモート / Dynabook 側の前提

- 以前のブートストラップ記録では sshd は running、22/tcp は listen していた。
- ただし、その後の接続試行では既存の手元鍵では認証できなかった。
- Dynabook 側の HTTP 系 read-only プローブは time out しており、実運用の接続確立は未完了。
- したがって、Dynabook での実行確認はまだ「到達待ち」。

### 5. 材料データの現状

- 一般材料の辞書は `[engines/fea/materials.json](/D:/Clawdbot_Docker_20260125/engines/fea/materials.json)` にある。
- 内容は `CuSn6`, `CuBe2`, `PBT_GF30`, `PA66_GF30`, `Steel_S45C`, `Steel_SUS304`, `Aluminum_A5052`, `Aluminum_A6061T6` などの構造材料。
- これは Moldflow の材料カード DB ではない。
- `[data/workspace/materials_project_api_status.json](/D:/Clawdbot_Docker_20260125/data/workspace/materials_project_api_status.json)` では Materials Project API が `api_ready`。
- ただし、そこにも「DBを丸ごとミラーしない」「利用規約を確認する」といった制約が明記されている。
- 今回の調査範囲では、Moldflow の proprietary material card を追加した痕跡は見つからなかった。

## 重要な差分

- 既存の文書や changelog では、Moldflow CAE Studio はすでに「基準点」「Gate Advisor」「learned params」「golden case」などの段階に進んでいる。
- 一方で、計算精度の本丸である商用 Moldflow との相関証跡は未完成。
- `docs/moldflow_accuracy_l3_to_l10_te_plan.md` にある通り、L6 以降は実測データが必要な領域がある。
- したがって、現段階で「Moldflow と同等の精度に到達した」とは言えない。

## Fable5 への引継ぎポイント

1. まずはアプリ本体の追跡先を固定すること。
2. 次に、API の待受ポートと UI 側の起動ポートの整合を再確認すること。
3. その後、材料データを「一般材料」「公開データ」「ライセンス許諾済み商用カード」に分けて扱うこと。
4. 商用 Moldflow の材料カードや相関データは、許可なしに複製しないこと。
5. 実測 or authorized benchmark がない限り、精度同等を主張しないこと。

## 参照ファイル

- `[docs/handover/MOLDFLOW_STUDIO_REFACTOR_STEP1_20260710.md](/D:/Clawdbot_Docker_20260125/docs/handover/MOLDFLOW_STUDIO_REFACTOR_STEP1_20260710.md)`
- `[docs/handover/MOLDFLOW_STUDIO_REFACTOR_STEP2_20260710.md](/D:/Clawdbot_Docker_20260125/docs/handover/MOLDFLOW_STUDIO_REFACTOR_STEP2_20260710.md)`
- `[docs/handover/MOLDFLOW_STUDIO_REFACTOR_STEP3_20260710.md](/D:/Clawdbot_Docker_20260125/docs/handover/MOLDFLOW_STUDIO_REFACTOR_STEP3_20260710.md)`
- `[docs/handover/MOLDFLOW_STUDIO_REFACTOR_STEP4_20260710.md](/D:/Clawdbot_Docker_20260125/docs/handover/MOLDFLOW_STUDIO_REFACTOR_STEP4_20260710.md)`
- `[quality_incident_report_20260711_moldflow_mcp_preflight.md](/D:/Clawdbot_Docker_20260125/quality_incident_report_20260711_moldflow_mcp_preflight.md)`
- `[data/workspace/moldflow_bridge/HANDOVER_20260711_moldflow_bridge.md](/D:/Clawdbot_Docker_20260125/data/workspace/moldflow_bridge/HANDOVER_20260711_moldflow_bridge.md)`

## 未解決

- Dynabook 側への安定接続。
- MCP ブリッジの write operations 解禁条件。
- Moldflow 材料カード DB の正規な追加元。
- 商用 Moldflow との相関評価データ。

