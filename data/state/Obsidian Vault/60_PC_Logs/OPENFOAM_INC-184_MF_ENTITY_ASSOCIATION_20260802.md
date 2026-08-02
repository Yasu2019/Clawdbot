# INC-184 Moldflow entity association mismatch

## QC工程表

| 工程 | 入力 | 管理項目 | NG時処置 |
|---|---|---|---|
| MF export | result CSV | result association | NODE/TRI3/1DETを明示 |
| geometry join | entity geometry | composite key | `(association, entity_id)`以外を禁止 |
| reference pack | MF results | reference-only provenance | solver loadへの混入禁止 |
| CalculiX deck | NODE+TRI3 | connectivity 100% | foreign nodeで停止 |
| validation | OF prediction vs MF | declared KPI gates | `PROXY_GAP`維持 |

## 事実

- `deflection_all_effects` と `temperature_nodal` はNODE関連。
- `volumetric_shrinkage_ejection` と主応力はTRI3関連。
- CSVの識別列名が `NodeID` でも、結果関連先はNODEとは限らない。
- NODE/TRI3/1DETの数値IDは重複し得る。
- 初回ベンチマーク生成はforeign-ID gateで安全停止し、原本・既存計算を変更していない。
- field-pack manifestはPython `json.loads`で合格し、Cooling STLパスも正しいUTF-8 JSONだった。先のPowerShell失敗は明示UTF-8なしの読込経路による文字化けだった。

## FTA / 5Why

トップ事象: 収縮場を節点場として誤結合する危険。

1. 全CSVの `NodeID` を節点IDと解釈した。
2. plotごとのassociationを入力契約に含めなかった。
3. 数値IDだけでgeometry namespaceを識別しようとした。
4. mixed association試験がなかった。
5. PowerShell側でUTF-8を明示せずmanifestを読んだ。

## Fishbone

- 人/判断: 列名を意味として扱った。
- データ: exporterの共通ヘッダ。
- 方法: association非明示のjoin。
- 設備/ソフト: Windows PowerShellの既定文字コード依存。
- 測定: mixed NODE/TRI3 coverage test不足。

## FMEAと対策

| Failure mode | RPN観点 | 対策 |
|---|---:|---|
| element fieldのnodal化 | 最大 | explicit association catalog |
| ID重複によるsilent join | 最大 | composite key |
| MF reference leakage | 最大 | reference/load物理分離 |
| encoding依存のmanifest読込 | 中 | Python strict parse gate / PowerShell UTF-8明示 |

## 恒久ルール

IF Moldflow fieldを取り込む THEN association metadataを検証し `(association, entity_id)` で結合する。CSV列名または数値IDだけからassociationを推定してはならない。

## 回復・検証

1. Python strict JSON parseを実行し、PowerShell利用時はUTF-8を明示。
2. NODEとTRI3を含むassociation matrix testを実行。
3. NODE 1818、TRI3 3552のgeometry整合を確認。
4. 参照場がCalculiX loadに含まれないことを検査。
5. 独立OpenFOAM履歴だけをload sourceとして許可。

検証完了までは `PROXY_GAP`。Moldflow同等の主張は禁止。
