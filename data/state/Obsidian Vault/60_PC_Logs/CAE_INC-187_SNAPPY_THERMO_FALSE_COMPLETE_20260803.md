---
incident: INC-187
date: 2026-08-03
machine: LAVIE
status: countermeasure_implemented_retry_pending
accuracy: PROXY_GAP
beads: Clawdbot_Docker_20260125-270e
---

# INC-187 OpenFOAM熱充填の辞書欠落と完了誤判定

## 影響と事実

対象trialは`lavie-mfminusx-thermo-fill-20260803`。OpenFOAM v2512は
`constant/thermophysicalProperties`欠落で99.87秒後に停止し、充填率は
0.01%、物理時間は進まなかった。Moldflow元データ、既存tri-track、失敗runは
変更・削除していない。監視表示だけが誤って完了になった。

## なぜなぜ・FTA・Fishbone

最上位事象は「熱充填が開始できず、監視が完了と表示」。生成系では
snappy選択が非熱MFALIGNテンプレートへ固定され、physics categoryが必要辞書を
追加しなかった。検査系ではsnappy+thermalの組合せ試験がなかった。通信系では
worker応答取得成功とsolver成功を同じ終了コードで扱った。配備系ではローカルと
LAVIEの版一致をtrial前条件にしていなかった。

## FMEA

| 故障モード | 影響 | 検出 | 恒久対策 |
|---|---|---|---|
| 熱物性辞書欠落 | solver即停止 | FOAM fatal | thermal overlayとfail-closed |
| T/p patch不一致 | field read失敗 | 生成物試験 | gate/vent/moldflow専用場を生成 |
| verdict誤読 | 無効runから冷却開始 | JSON照合 | nested verdictのみで成功判定 |
| LAVIE旧版 | 同じ障害再発 | hash比較 | dispatch前hash gate |

## QC工程表

| 工程 | 管理項目 | 合格基準 | 異常時処置 |
|---|---|---|---|
| Case生成 | thermo必須ファイル | 全9辞書と0/T,0/pあり | dispatch禁止 |
| 境界条件 | patch名 | gate/vent/moldflow一致 | case再生成 |
| 配備 | K10/LAVIE hash | 対象コード一致 | 同期後に再照合 |
| Solver | verdict/時間 | SUCCESSかつtime>0 | FAILED記録、次段禁止 |
| 比較 | MF対OF KPI | 単位・座標・誤差表あり | PROXY_GAP維持 |

## 対策・ロールバック・検証

`moldflow_step_case_builder.py`へ熱物性/solver辞書とT/pのoverlayを追加。
待機処理はJSON内`trial_entry.verdict`を解析しFAILEDを完了扱いしない。
再試行準備の初回でbusy応答にもverdict ERRORが付く境界条件を検出したため、
worker_busyをsolver verdictより先に分類する対策も追加した。solverは未起動。
回帰試験とpy_compileはPASS。バックアップは
`backup/inc187-before-thermo-overlay-20260803` / `49e1b837fd`。
失敗runは証拠として保存し、再試行は新しいr2 IDのみ使用する。

## 限界と次実験

対策はコード経路の再発防止まで。熱充填・閉ゲート冷却・Moldflowとの温度、
充填、圧力、ウェルド、反り、ヒケ一致は未検証であり、等価性を主張しない。
次はLAVIE hash一致、最終case precheck、r2実計算の順で確認する。

## r3再投入

r2はworker取得後、LAVIE repo側の`resin_fill_v007`元テンプレート欠落を
fail-closedで検出し、solverを起動せず終了した。9ファイルを仮名取得、SHA-256
照合、既存ファイルの`*.inc187_pre_r3_20260803`退避後に配置した。新ID
`lavie-mfminusx-thermo-fill-r3-20260803`を23:26 JSTに投入し、既存tri-trackを
維持したまま30秒間隔のbounded waitへ移行した。
