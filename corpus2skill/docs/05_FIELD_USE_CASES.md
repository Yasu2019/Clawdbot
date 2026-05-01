# 05 現場ユースケース

## IATF内部監査質問生成
質問: 「製造工程監査で確認すべき8.5関連の証跡は？」
探索:
1. IATF root
2. Clause 8
3. 8.5
4. 社内工程管理規定
5. QC工程表
6. 監査記録
回答:
- 条項
- 社内ルール
- 必要証跡
- 質問例
- 不足資料

## QC工程表から異常処置確認
質問: 「プレス工程で寸法外れが出た場合の処置は？」
探索:
1. QC工程表 root
2. Process Flow → Press
3. Control Items → Dimensions
4. Abnormal Handling
5. Records

## 図面・GD&T確認
質問: 「Datum C-Cはどの面から構成されるか？」
探索:
1. Drawing root
2. Datum System
3. C-C candidate
4. PDF locator
5. STEP face candidates
6. human_verified flag

## 不具合原因探索
質問: 「シミムラの原因候補と過去対策は？」
探索:
1. Defect root
2. Phenomenon
3. Occurrence Process
4. Similar cases
5. Corrective actions
6. Effectiveness check

