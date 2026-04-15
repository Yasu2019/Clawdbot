# Manufacturing Engineering Simulator Pro

現場そのまま再現版（プロ仕様）のベースプロジェクトです。  
Claude / Codex にそのまま渡し、さらに高度化させる前提で整理しています。

## 含まれる機能
- 射出成形: 充填率、ヒケ、ショート、バリ、反り
- 金属プレス: スプリングバック
- レベラー概念: 多ロール矯正の簡易傾向
- 母材＋めっき＋リフロー: 温度プロファイル、液相率、濡れ性、界面応力
- Niストライク比較: 界面拡散、濡れ性、ボイド傾向
- IMC成長: Cu6Sn5 / Cu3Sn / Total IMC
- CSV重ね表示

## 実行方法
```bash
pip install -r requirements.txt
streamlit run app.py
```

## 重要
このアプリは教育・仮説整理用の簡易モデルです。
厳密設計、保証判断、顧客提出には実測・CAE・材料データと併用してください。
