# スパゲッティ図 分析レポート

## 1. タグ別サマリー
| tag_id         | start               | end                 |   duration_sec |   samples |   distance_m |   avg_speed_m_s |   max_speed_m_s |   outlier_count |
|:---------------|:--------------------|:--------------------|---------------:|----------:|-------------:|----------------:|----------------:|----------------:|
| worker_anon_01 | 2026-05-01 09:00:00 | 2026-05-01 09:03:48 |            228 |       229 |       21.677 |           0.095 |           0.206 |               0 |

## 2. ゾーン滞在時間
| tag_id         | zone_id   |   dwell_sec |   samples |   dwell_ratio |
|:---------------|:----------|------------:|----------:|--------------:|
| worker_anon_01 | INSPECT_4 |          70 |        71 |     0.307018  |
| worker_anon_01 | INSPECT_5 |          69 |        69 |     0.302632  |
| worker_anon_01 | BUFFER    |          42 |        42 |     0.184211  |
| worker_anon_01 | OUTSIDE   |          31 |        31 |     0.135965  |
| worker_anon_01 | BOX       |          16 |        16 |     0.0701754 |

## 3. ゾーン遷移
| tag_id         | from_zone   | to_zone   |   count |
|:---------------|:------------|:----------|--------:|
| worker_anon_01 | BUFFER      | OUTSIDE   |       2 |
| worker_anon_01 | INSPECT_4   | OUTSIDE   |       2 |
| worker_anon_01 | OUTSIDE     | INSPECT_5 |       2 |
| worker_anon_01 | OUTSIDE     | BUFFER    |       2 |
| worker_anon_01 | INSPECT_5   | OUTSIDE   |       1 |
| worker_anon_01 | BOX         | OUTSIDE   |       1 |
| worker_anon_01 | OUTSIDE     | BOX       |       1 |
| worker_anon_01 | OUTSIDE     | INSPECT_4 |       1 |

## 4. ムダ動線候補
| tag_id         | pattern                | severity   | timestamp           | detail                | suggestion                                                   |
|:---------------|:-----------------------|:-----------|:--------------------|:----------------------|:-------------------------------------------------------------|
| worker_anon_01 | レイアウト外滞在が多い | medium     | 2026-05-01 09:00:00 | OUTSIDE dwell=31.0sec | レイアウトゾーン定義不足、または作業範囲外への移動を確認する |

## 5. 改善確認の見方
- A-B-A往復が多い場合：置き場の手元化、外段取り化、補充方法の見直し
- ラベル/箱/治具置場への往復が多い場合：3定5Sとミズスマシ化を検討
- OUTSIDEが多い場合：ゾーン定義不足、または想定外動線を確認
- 速度外れ値が多い場合：UWB NLOS、アンカー配置、フィルタ設定を確認