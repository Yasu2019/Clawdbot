# 改善前後 スパゲッティ図比較レポート

## 1. 改善前後サマリー
| tag_id         |   before_distance_m |   after_distance_m |   distance_reduction_m |   distance_reduction_ratio |   before_duration_sec |   after_duration_sec |   before_patterns |   after_patterns |
|:---------------|--------------------:|-------------------:|-----------------------:|---------------------------:|----------------------:|---------------------:|------------------:|-----------------:|
| worker_anon_01 |              44.954 |             21.677 |                 23.277 |                     0.5178 |                   426 |                  228 |                 1 |                1 |

## 2. 判定目安
- 歩行距離が20%以上減少：レイアウト改善効果あり
- ムダ動線候補が減少：置き場・外段取り化の効果あり
- 距離が減ってもCTが悪化：検査順序、品質確認、手元作業の再分析が必要

## 3. OpenCodeGOレビュー指示
`opencodego/prompts/spaghetti_review_prompt.md` に比較CSVを添付してレビューさせてください。