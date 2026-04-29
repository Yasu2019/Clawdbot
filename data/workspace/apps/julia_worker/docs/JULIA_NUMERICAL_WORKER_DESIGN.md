# Julia Numerical Worker Design

## 採用理由

Juliaは以下に強いです。

- 数値計算
- 最適化
- 線形代数
- 微分方程式
- JITによる高速化
- Pythonとの相互運用

## Clawstack内での位置づけ

```text
Python = 司令塔、API、帳票、RAG、Web
Julia  = 高速計算Worker
CAE    = 正式ソルバー
```

## 今後追加候補

- JuMPによる数理最適化
- DifferentialEquations.jlによる簡易物理モデル
- CSV/Parquet入力
- Qdrantから条件履歴を取得して最適化
- OpenFOAM/Elmer/CalculiXケース生成補助
- レベラー専用の曲率・応力近似モデル強化
- PrePoMax/CalculiX結果の後処理
