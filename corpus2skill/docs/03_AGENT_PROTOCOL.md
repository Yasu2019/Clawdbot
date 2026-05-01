# 03 Navigator Agent プロトコル

## 役割
Navigator Agent は、検索結果をそのまま信じず、文書ツリー内を探索して根拠を集めるエージェントです。

## 基本ループ
1. user_query を受け取る
2. root_summary を読む
3. 候補branchを選ぶ
4. branch_summaryを読む
5. 必要ならleafへ降りる
6. evidence_idを取得
7. 不足なら戻って別branchへ
8. 回答と引用を生成
9. navigation_logを保存

## 停止条件
- 十分な根拠が2件以上ある
- 主要文書と補助文書の整合が取れた
- 最大探索ステップに到達
- 根拠が見つからず「不明」と判断

## 禁止事項
- evidence_idなしで断定しない
- 1つの検索結果だけで結論にしない
- IATF条項番号を推測で補完しない
- 図面datumを推測だけで確定しない
- QC工程表の管理値を類似文書から流用しない

