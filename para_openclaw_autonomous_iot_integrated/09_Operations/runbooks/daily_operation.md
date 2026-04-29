# 日次運用

1. 90_Inboxを確認。
2. dry-run分類を実行。
3. レポートで低信頼度ファイルを確認。
4. 問題なければ apply。
5. RAG enqueue stubで候補数を確認。
6. 異常CSVがあれば iot_anomaly_detector.py を実行。
7. Past_Troublesに異常サマリーを蓄積。
