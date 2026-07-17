# 成功事例集 (Success Cases) — ローカルLLM参照用

目的: 高難度問題の解決過程を「再利用できる形」で残す。全エージェントは成功時にここへ追記する。
指南書: `docs/LOCAL_LLM_CODING_PLAYBOOK.md` / 失敗集: `trouble_history.md`

**追記の型 (1事例=1節、この5項目を必ず)**
```
## [S###] タイトル (日付, 担当)
- 問題: 何が起きていたか (症状)
- 診断: どうやって根本原因に到達したか (見た実物・使った数値)
- 解決: 何をどう変えたか (最小変更で)
- 証拠: 成功をどう確認したか (実測値)
- 再利用: 次に同種問題が来たらどうするか (1-2行)
```

---

## [S001] Moldflow充填が「板のまま」→3層の根本原因を実物検証で特定 (2026-07-15, Fable5)
- 問題: カスタムSTLの充填動画依頼後もTelegramには100x60x2板の動画のみ。
- 診断: ①run_dirの時系列ディレクトリ有無→ソルバー未実行と確定 ②ログのdeltaT数列→1e-16に崩壊=発散 ③checkMeshでメッシュ体積318cm³ vs 部品体積42cm³→「部品の外側」を解いていたと数値で確定。保持点(0,0,0.025)が中空部だった。
- 解決: locationInMeshを肉厚2mm内部(-0.049,0,0.025)へ(STLをレイキャスティングで解析して算出)。ゲート/ベントはtopoSet cylinderToFace+patchToFace subsetで部品表面に生成。Courant上限20→1.0/0.5。
- 証拠: checkMesh品質OK・alpha有界[0,1]・実CFD動画がTelegram到達。
- 再利用: 「充填がおかしい」→ まずメッシュ体積÷部品体積を計算。>1.5なら外部流。保持点は必ず肉の内部。詳細: trouble_history [T064]。

## [S002] batダブルクリックが無言で不発 → 原因は改行コードLF (2026-07-15, Fable5)
- 問題: Explorerから.batを起動してもログが書かれず、コンソールも残らない。
- 診断: 同フォルダの別batは動く→内容差分ではなく生成方法の差。AIツールのファイル書き込みはLF改行 → cmd.exeはCRLF前提。
- 解決: `sed 's/$/\r/'` でCRLF化+ASCII化したbatを再生成 → 即起動。
- 証拠: 同一内容のCRLF版が一発で動作 (solder_demo.log 18:17 start)。
- 再利用: AIが生成するbatは必ずCRLF。日本語echoは避ける(CP932文字化け)。失敗時にconsoleが残るよう `pause` を必ず入れる。

## [S003] 半田データセット判定が全件同一スコア → エンジン選定で解決 (2026-07-15, Fable5)
- 問題: solder-joint-dataset評価で全18枚がscore 1.0000=識別力ゼロ。
- 診断: ①normalが6枚しか読めていない→拡張子.tiff未対応(find実物確認) ②修正後も全件1.0→参照差分方式は切り出しサイズ不揃い画像に原理的に無力(T050の実測と一致)。
- 解決: ①tiff対応のローカルimgs_in追加(共有関数は不変更) ②NTFS大小文字非区別の重複をsetで排除 ③エンジンをPatchCoreへ。
- 証拠: 正常2枚(2.76/3.25) vs 不良16枚(3.26-4.06)=全不良が全正常より高スコア(順位分離100%)。
- 再利用: 新データセットはまず拡張子・枚数・サイズ分布を実測。切り出し画像→PatchCore。閾値は全数評価で決める。

## [S004] DoEエンジンを実解析に接続 (モック排除パターン) (2026-07-15, Fable5)
- 問題: D/I最適計画がモックKPI上で動いており"最適解"が式に埋め込まれた答えだった(T063)。
- 解決: scripts/moldflow_doe_real_trials.py — 計画点→cae_te_remote_trial.py実試行→KPIスクリプトの実測値でRSM更新。連続3失敗で停止する意味ゲート+state.json再開+通知なし(summary.mdのみ)。
- 証拠: D/I計画生成→RSM適合→最適点探索の全経路をテスト済(設計10点×2変数)。
- 再利用: 最適化ループを作る時はこのファイルを雛形にする。KPIは必ず解析出力ファイル由来。

## [S005] 既存WebUIへの機能追加はクライアント側集計で無停止反映 (2026-07-15, Fable5)
- 問題: 外観検査AIにタグ検索・判定事例ページを追加したいがAPI再起動はリスク。
- 解決: /api/samplesの既存データをapp.js側で集計(タグ導出・グループ化)する設計にし、サーバ変更ゼロ。record_sampleには後方互換のtags引数のみ追加。
- 証拠: ブラウザ再読込のみで2タブ稼働。既存タブ・API無変更。
- 再利用: 表示系の追加はまずクライアント側集計で実現できないか検討。サーバ変更は最終手段。

## [S006] Moldflow 2010の既存ゲートをMCPで非破壊確認 (2026-07-16, Codex)
- 問題: メッシュはMCPで確認できたが、Synergy上で設定済みの射出ゲートをMoldflow 2010 COMから直接読めなかった。
- 診断: Autodeskの採用解でNDBCの直接getterが存在せず、一時UDMを読む必要があると判明。配置後も旧PIDが応答していたため、ファイル更新と実行中バージョンを分離して検証した。
- 解決: 読取専用UDM export、NDBC型40000/40002/40003抽出、ノード座標照合、一時UDM削除を既存MCP inspectorへ追加した。
- 証拠: 実機MCPがgate_count=1、node_id=2、座標(-50.0000007451, 2.7391463518, 23.8075219095)、cleanup_error=0、analysis_started=falseを返した。
- 再利用: IF Moldflow 2010の既存射出位置を読む THEN UDM/NDBCを解析 BECAUSE 公式APIに直接getterがない。配布後はhashとlive responseを確認する。

## [S007] Moldflow 2010のコピー限定AutoFixをMCP実行 (2026-07-16, Codex)
- 問題: メッシュ診断APIが150～180秒で停止し、GUI修復しかできないように見えた。
- 診断: 実機`synapi.chm`から`MeshEditor.AutoFix()`と`DuplicateStudyByName2()`を発見。初回は表示名とSDY名の記号差で安全停止した。
- 解決: Study名を英数字だけに正規化し、既存`copy 2`を再利用するコピー限定ツールを実装した。
- 証拠: AutoFixが580件除去、Save=True、analysis_started=false。元StudyへAutoFixは実行していない。
- 再利用: IF Moldflow書込み操作 THEN 元Studyを複製しcanonical name一致後のみ実行。表示名とSDYファイル名を直接比較しない。

## [S008] Dynabook Moldflow 2010のFusionメッシュをMCPから開始 (2026-07-17, Codex)
- 問題: VPN、8765/8766混在、Python環境、bind policy、COM bitness、通常GUIとAutomationの競合により、MCPからメッシュ生成へ到達できなかった。
- 診断: 各層を独立検証し、Synergy COMが64-bit registry viewのみ、MCPは専用venv必須、`MeshNow(False)`は非同期であることを実機値から確定した。
- 解決: copy名一致・write gate・64-bit cscript・3回限定COM retryを持つ `moldflow_mesh_active_study_copy` と明示node限定の `moldflow_set_gate_active_study_copy` を実装・配備した。
- 証拠: 7 tests PASS、remote SHA一致、live MCP tool list確認、Version 2010/active project/study確認、3.0 mm mesh start error 0、UI進捗30%、analysis false。
- 再利用: IF Moldflow 2010 MCP書込み THEN VPN/service/interpreter/bind/COM/session/study identityを順にゲートし、`Running`を成功途中状態としてpollする。完了前に再実行しない。
