# スパゲッティ図 分析レポート

## 1. タグ別サマリー
| tag_id         | start               | end                 |   duration_sec |   samples |   distance_m |   avg_speed_m_s |   max_speed_m_s |   outlier_count |
|:---------------|:--------------------|:--------------------|---------------:|----------:|-------------:|----------------:|----------------:|----------------:|
| worker_anon_01 | 2026-05-01 09:00:00 | 2026-05-01 09:07:06 |            426 |       427 |       44.954 |           0.105 |           0.223 |               0 |

## 2. ゾーン滞在時間
| tag_id         | zone_id   |   dwell_sec |   samples |   dwell_ratio |
|:---------------|:----------|------------:|----------:|--------------:|
| worker_anon_01 | OUTSIDE   |         122 |       122 |     0.286385  |
| worker_anon_01 | INSPECT_4 |         121 |       122 |     0.284038  |
| worker_anon_01 | INSPECT_5 |          91 |        91 |     0.213615  |
| worker_anon_01 | BOX       |          45 |        45 |     0.105634  |
| worker_anon_01 | LABEL     |          36 |        36 |     0.084507  |
| worker_anon_01 | BUFFER    |          11 |        11 |     0.0258216 |

## 3. ゾーン遷移
| tag_id         | from_zone   | to_zone   |   count |
|:---------------|:------------|:----------|--------:|
| worker_anon_01 | BUFFER      | OUTSIDE   |       4 |
| worker_anon_01 | OUTSIDE     | BUFFER    |       4 |
| worker_anon_01 | OUTSIDE     | INSPECT_5 |       3 |
| worker_anon_01 | INSPECT_4   | OUTSIDE   |       3 |
| worker_anon_01 | OUTSIDE     | INSPECT_4 |       3 |
| worker_anon_01 | INSPECT_5   | OUTSIDE   |       3 |
| worker_anon_01 | BOX         | OUTSIDE   |       2 |
| worker_anon_01 | LABEL       | OUTSIDE   |       2 |
| worker_anon_01 | OUTSIDE     | BOX       |       2 |
| worker_anon_01 | OUTSIDE     | LABEL     |       2 |

## 4. ムダ動線候補
| tag_id         | pattern                | severity   | timestamp           | detail                 | suggestion                                                   |
|:---------------|:-----------------------|:-----------|:--------------------|:-----------------------|:-------------------------------------------------------------|
| worker_anon_01 | レイアウト外滞在が多い | medium     | 2026-05-01 09:00:00 | OUTSIDE dwell=122.0sec | レイアウトゾーン定義不足、または作業範囲外への移動を確認する |

## 5. 改善確認の見方
- A-B-A往復が多い場合：置き場の手元化、外段取り化、補充方法の見直し
- ラベル/箱/治具置場への往復が多い場合：3定5Sとミズスマシ化を検討
- OUTSIDEが多い場合：ゾーン定義不足、または想定外動線を確認
- 速度外れ値が多い場合：UWB NLOS、アンカー配置、フィルタ設定を確認