# INC-185 Scorecard zero-error判定不具合

## 事実

- MFとOFが完全一致すると相対誤差は`0.0`。
- 既存式`_rel(...) or 99`は`0.0`をfalseとして99へ置換した。
- r33の圧力差41.46%は非ゼロなので、現状の`PROXY_GAP`判定は正しい。
- 原因はローカルPython意味論で完全に特定でき、Web調査は対策を変えないため実施しない。

## QC工程表

| 工程 | 管理点 | 合格条件 |
|---|---|---|
| KPI差分 | Noneと0の分離 | 0を保持 |
| tolerance | 境界値 | below/at/aboveを試験 |
| promotion | mandatory KPI | 全項目Trueのみ昇格 |
| 実データ再試験 | r33圧力 | 41.46%差でPROXY_GAP |

## 5Why / FTA

トップ事象は誤った昇格判定。直接原因はboolean fallback、流出原因はゼロ境界試験不足。完全一致をfalse扱いし、欠測sentinelと混同した。

## FMEA

| Failure mode | 影響 | 対策 |
|---|---|---|
| zero->99 | false fail | `is None`分岐 |
| fill-only昇格 | false pass | mandatory全合格 |
| 境界丸め | 判定不安定 | tolerance matrix |

## 恒久対策

IF 数値誤差が0.0 THEN 有効な完全一致として保持する。欠測代替は`None`の場合だけ許可する。

検証完了までは`PROXY_GAP`を維持する。
