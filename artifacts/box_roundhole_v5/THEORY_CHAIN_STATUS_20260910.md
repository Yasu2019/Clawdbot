# 理論連成チェーンの実装状況

## 実装済み

- `scripts/material_chain.py`
  - 二領域Tait型の `rho(p,T)` と等温圧縮率
  - 圧力依存を含むCross-WLF粘度
  - 単調PVT表の双線形補間
  - 安定化した熱収縮ひずみ
- `tests/test_material_chain.py`：6 tests passed
- `compressibleInterFoam` の熱物性ケースで、圧力・温度依存EOSの短時間実行を再確認
- ケース生成時に `constant/crossWLFProperties` と `constant/pvtTable.csv` を出力

## まだ厳密な実ソルバー連成ではない部分

1. `rPolynomial` は厳密な非線形Tait EOSではなく、OpenFOAM標準EOSによる局所近似。
2. Cross-WLFパラメータはカード化済みだが、stock `compressibleInterFoam` の
   generalized-Newtonian transportプラグインは未コンパイル。
3. PVT表は仮想2x2表であり、実測表ではない。
4. 熱収縮場はCalculiXへの受け渡し準備段階で、冷却履歴からの完全な構造再解析は未実行。

したがって現段階の正式な表記は、**理論チェーン実装済み・OpenFOAM EOS検証済み・
Cross-WLF/PVT/反りはスクリーニング連成準備済み（実測校正前）** とする。
