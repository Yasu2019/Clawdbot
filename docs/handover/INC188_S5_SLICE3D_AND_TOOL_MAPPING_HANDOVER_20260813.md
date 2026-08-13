# INC-188 引き継ぎ — S5 打ち抜き成立 と 工具マッピング確定 (2026-08-13)

対象: MR536 (AA5052-H34) t=0.51mm の順送打ち抜き / OpenRadioss
前提文書: `docs/handover/INC188_SHEAR_BLANKING_HANDOVER_20260811.md`（材料校正・棄却仮説はそちらが正）
本書はその**続き**。08-11 以降に (a) slice3D で打ち抜きが初めて成立し、(b) PPTX/PDF/STEP から工具名と幾何が確定した。

Beads: `Clawdbot_Docker_20260125-zntq`（本作業）/ `-n47u`（GENE1 校正）/ `-vkc3`（校正の根本課題）

---

## 0. 先に読むこと — 破棄すべき先行報告

2026-08-13 に別エージェントが `opus5_handover_knowledge_graph.md` を作成したと報告したが、
**そのファイルは D:/デスクトップ/ユーザープロファイルのいずれにも存在しない**。
併せて報告された物理値も本リポジトリの記録と矛盾する。**引き継がないこと。**

| 先行報告の主張 | 実際 | 根拠 |
|---|---|---|
| 「100% Zero-Gap 接触制約」を獲得した物理法則として提示 | **正反対**。隙間ゼロでは剪断帯が立たない（2DA で実証済み）。工具すきま 5µm < Gap_max 15µm < ダイ隙間 40µm を守る | `scripts/build_inc188_slice3d.py:46-49` |
| 破壊則は Cockcroft-Latham | **`/FAIL/GENE1`**（`Eps_eff`）。CL は使っていない | `build_inc188_slice3d.py:109`, INC188AC デック |
| 最大主応力 σ₁ = 580 MPa | 材料の実測 UTS は **249.5 MPa**。580 MPa は 2.3 倍で成立しない | `MR536_SS曲線データ.xlsx` / 08-11 文書 §2 |
| ストローク 3.60 mm (貫入 720%) | パンチ目標は **-2.0 mm**。S5 は 51 要素 = 板厚 0.51mm 貫通で成立 | `openradioss_4mmx4mm_assy_params.py:26`, bd `gloi` notes |
| 丸パンチ ∅0.90 mm | **∅0.56 mm**（R0.28 の円筒面1枚） | STEP 実測（本書 §2） |
| 235倍顕微鏡視野で 2〜5µm 微小クラック予測 | 要素寸法が **10 µm**。2〜5µm は解像できない | `build_inc188_slice3d.py:43` |
| 工具IDはINPのエルセット名 | STEP の PRODUCT 名。INP のエルセットは4つのみで**パンチは工具別に分離されていない** | 本書 §2・§3 |
| INP 11,482 ノード | **11,483** ノード（要素 51,621 C3D4 は一致） | INP 実測 |

---

## 1. 工具の正式名称と対応（PPTX / 図面PDF / STEP の三者一致）

`Panel_3D_Model_20260813.pptx`（スライド1枚）と `4mmx4mm.pdf` のラベルは同一で、**4種**:

| 図面ラベル | STEP PRODUCT 名 | 位置 | 形状 |
|---|---|---|---|
| トリムパンチ | `Trim1_001` | 右上 | 斜めトリム輪郭 |
| 四角パンチ ① | `Rectangle1_001` の一部 | 左 | **V字ノッチ（＜形）**。45°の細スロット2本 |
| 四角パンチ ② | `Rectangle1_001` の一部 | 右下 | 矩形段差 2.569 × 6.760 mm |
| 丸パンチ | `hole1_001` | 中央 | **∅0.56 mm** 貫通 |
| （ラベルなし） | `Die1_001` / `Stripper1_001` | 下/上 | 外形板（PPTXには記載なし） |

**要注意**: 「四角パンチ」は2工具だが、STEP 上は `Rectangle1_001` **単一ソリッドに3領域**が同居している
（V字ノッチを構成する斜めスロット2本 + 右下矩形1個）。工具別に切り出す処理が別途必要。
左の①は「直角工具」ではなく**V字ノッチ**である（先行報告の誤り）。

---

## 2. STEP 実測値 — `ASSY_3D-MPM_PM7T1C_20260813.step`

アセンブリ構成は `NEXT_ASSEMBLY_USAGE_OCCURRENCE` 6件、各部品1インスタンス。

| 部品 | ソリッド数 | 面 | 円筒面 | X範囲 [mm] | Y範囲 [mm] | Z範囲 [mm] |
|---|---|---|---|---|---|---|
| `OpenRadioss_PM7T1C_20260101_dxf1_001`（板） | 1 | - | - | 177.180–192.210 | -1890.055 – -1874.630 | 0–0.5 |
| `Die1_001` | 1 | - | - | 176.882–192.210 | -1890.055 – -1874.630 | 0–0.5 |
| `Stripper1_001` | 1 | - | - | 176.882–192.210 | -1890.055 – -1874.630 | 0–0.5 |
| `Rectangle1_001` | 1 | 20 | 8 | 178.124–188.530 | -1889.664 – -1880.520 | 0–0.5 |
| `Trim1_001` | 1 | 18 | 9 | 176.902–192.210 | -1884.296 – -1874.630 | 0–0.5 |
| `hole1_001` | 1 | 3 | 1 | 中心 185.657 | 中心 -1882.188 | 0–0.5 |

**この STEP は工具アセンブリではない。** 全部品の Z が板厚と同じ 0–0.5 mm で、`Die1_001` と
`Stripper1_001` は板と同一外形。すなわち「どの領域をどの工具が抜くか」の**平面レイアウト図**であり、
上下に実体を持つ工具ソリッドは含まない。FEM 用アセンブリとしてそのままは使えない。

コーナR: `Rectangle1_001` = R0.224 一律 / `Trim1_001` = R0.22, 0.478, 0.538, 2.7303, 3.205, 4.145, 6.024, 6.9644 / `hole1_001` = R0.28。

座標は元図面のグローバル系（Y ≈ -1880 台のオフセット付き）。原点移動が必要。

---

## 3. 旧 INP / RAD（2026-01 世代・現行解析では未使用）

`4mmx4mm_ASSY_20260104.inp`: 11,483 ノード / 51,621 要素 (C3D4)。エルセットは4つのみ。

```
Solid_part-Stripper / Solid_part-Die / From_parts-Material / From_parts-Punch
```

**3種のパンチは `From_parts-Punch` に統合されており、工具別に分離されていない。**
順送の多段解析をやるなら、ここを工具別に分けるところから。

`4mmx4mm_ASSY_20260105_0000.rad`（単位系 kg-m-s）の内容と現状の差異:

| 項目 | 旧 RAD | 現行（正） |
|---|---|---|
| 板材 | `/MAT/LAW2/2` `1060_Alloy_Plastic` ρ=2700, E=6.9e10, ν=0.33, a=200MPa, b=150MPa, n=0.20 | **AA5052-H34**。E=67,914MPa, a=196.4MPa, b=524.73MPa, n=0.7183（08-11 §2） |
| 工具 | `/MAT/LAW1/1` `S185_Steel` ρ=7800, E=2.1e11, ν=0.28 | 変更なし |
| 破壊則 | **`/FAIL` カードなし**（`EPS_p_max=1.0` のみ） | `/FAIL/GENE1` `Eps_eff` |
| パンチ速度 | `/FUNCT/1` で -0.05 m/s (=50 mm/s) | DOE。既定 5000 mm/s、上限 6100 mm/s |
| 接触 | `/INTER/TYPE25` ×3（Punch/Die/Stripper – Material） | TYPE25 を踏襲 |

デックのラベル `1060_Alloy_Plastic` は**誤り**（08-11 で確定済み）。旧資産を流用する際は必ず差し替えること。

---

## 4. 現在の解析状態 — slice3D で打ち抜きが成立した

3D フル模型では輪郭破断が 9% で頭打ちだったため、**切断線断面の1要素厚 3D スライス**へ移行した
（08-11 §6 の推奨1を実行）。ビルダ: `scripts/build_inc188_slice3d.py`。

### モデル定数

| 定数 | 値 | 意味 |
|---|---|---|
| `THICKNESS` | 0.51e-3 m | 板厚 |
| `DEFAULT_SHEAR_ELEM` | 10 µm | せん断帯の要素寸法 |
| `DEFAULT_CLEARANCE` | 40 µm | ダイ隙間（板厚の約7.8%）。**ゼロだと剪断帯が立たない** |
| `TOOL_GAP` | 5 µm | 工具-板の初期すきま（初期貫入エラー回避） |
| `DEFAULT_GAP_MAX` | 15 µm | 接触ギャップ上限。**TOOL_GAP < Gap_max < CLEARANCE** を必ず満たすこと |
| `DEFAULT_STFAC` | 1.0 | 接触剛性。AC の 0.05 は 10µm メッシュに柔らかすぎた |
| `DEFAULT_NSTEP` | 10 | 破断応力を落とすサイクル数。Altair 既定。**0 は爆発する** |
| `DEFAULT_SLICE` | 20 µm | X方向スライス厚（1要素） |

### S1 → S5 の履歴

| Trial | 変更 | 結果 |
|---|---|---|
| S1 | TYPE7 接触 | NORMAL TERMINATION / 1.58M cycle だが **削除0**。塑性ひずみ全要素 0.0、Von Mises 最大 12.61 Pa。パンチが板をすり抜けた。真因は破壊則ではなく **接触ギャップ0**（TYPE7 の Gap_scale/Gap_max/GAPmin/Igap すべて0、ソリッドは板厚を持たないので接触が起動しない） |
| S2–S4 | TYPE25 移植・接触ギャップ付与 | 荷重は立つが曲げで切れる |
| **S5** | **y=0 対称拘束 + TYPE25 + Stfac=1.0 + Nstep=10** | **NORMAL TERMINATION / 1,756,501 cycle / 破断 51 要素 = 0.51mm ÷ 10µm = 板厚貫通クラック1本。成立。** |

S5 のエネルギー収支: 閉じ率 97.1%（PLASTIC 90.3% / CONTACT 3.9% / KINETIC 0.7% / INTERNAL 2.2% / HOURGLASS 1.8e-36）。
断面プロットでスラグが平行に降下し、ストリップが z=0–0.51mm に留まることを確認済み。

**ソルバの ERR = -97.0% は物理エラーではない。** `(I+K-W)/W` が塑性散逸を含まないため、
塑性が支配的なモデルでは構造的に負に出る。ERR で合否を判定しないこと（08-11 §4 と同旨）。

### 直前の真因2件（再発させない）

1. **接触ギャップ0** → ソリッド要素では接触が起動せず、荷重ゼロのまま工具が貫通する（S1）
2. **y=0 の対称拘束欠落** → 板が剪断でなく曲げで切れる（commit `1fde82f0`）

---

## 5. 実行中のジョブ（2026-08-13 21:10 時点）

`Clawdbot_Docker_20260125-n47u` の GENE1 校正スイープが**稼働中**。

```
INC188_S_C3   (13:24 起動, A001–A009 出力継続中)
INC188_S_C6   (13:24 起動)
INC188_S_C10  (20:44 起動, A002 = 21:08)
INC188_S_NF   (13:24 起動, 破壊則なし参照)
```

引き継ぎ側は**まずこれらの完了状態を確認する**こと（`clawstack_v2/data/work/INC188_S_*T01.csv`）。

---

## 6. 未解決事項と次の一手

| # | 事項 | 内容 |
|---|---|---|
| 1 | **GENE1 が未校正**（最重要 / bd `n47u`・`vkc3`） | `Eps_eff=0.12` は文献帯からの推定値。DB に `literature_band_estimate` / `usable_for_calibration=0` で記録済み。S5 の破断完了は**貫入約13%**で、アルミの一般帯 20–40% より早い |
| 2 | 荷重-ストローク基準の取得 | パンチは変位制御なので **F = dW/ds**（S5 の T01 外部仕事から算出可能、再計算不要）。解析式 F = L·t·τs（AA5052-H34）とピークを突き合わせ、`Eps_eff` を掃引して**ピーク荷重と破断貫入率の両方**を合わせる |
| 3 | 工具別の切り出し | `Rectangle1_001` の3領域を工具②③に分離。INP の `From_parts-Punch` も同様 |
| 4 | STEP を FEM 用に立体化 | 現STEPは平面レイアウト。工具に実体高さを与える必要あり |
| 5 | 順送多段化 | 上記1–4が済むまで着手しない（校正なしに多段を積んでも意味がない → T019） |
| 6 | スラグ挙動 | S5 でスラグは降下するが、分離後の挙動は未評価 |

---

## 7. ファイルパス全一覧

### ユーザー提供資料
```
C:\Users\yasu\OneDrive\デスクトップ\Panel\Panel_3D_Model_20260813.pptx       工具名（スライド1枚）
C:\Users\yasu\OneDrive\デスクトップ\Panel\4mmx4mm.pdf                        図面（工具位置ラベル付き）
C:\Users\yasu\OneDrive\デスクトップ\Panel\ASSY_3D-MPM_PM7T1C_20260813.step   新STEP（平面レイアウト）
C:\Users\yasu\OneDrive\デスクトップ\Panel\4mmx4mm_ASSY.step                  旧STEP（部品名 Cut/Cut001…、対応不明）
C:\Users\yasu\OneDrive\デスクトップ\Panel\4mmx4mm_ASSY_20260104.inp          旧INP 11,483節点/51,621要素
C:\Users\yasu\OneDrive\デスクトップ\Panel\4mmx4mm_ASSY_20260105_0000.rad     旧RADスターター
C:\Users\yasu\OneDrive\デスクトップ\Panel\MR536_SS曲線データ.xlsx            実測SS曲線（※08-11の断面積補正を必ず適用）
C:\Users\yasu\OneDrive\デスクトップ\Panel\残留応力マッピング_スポット溶接部の3軸応力解析.jpg
C:\Users\yasu\OneDrive\デスクトップ\Panel\社内用_V分析Rev01_20250502.pptx
C:\Users\yasu\OneDrive\デスクトップ\Panel\試験結果_ミツイ精密_20250630.pdf
```
（注: `MR536_SS曲線データ.xlsx` は実ファイル名が `MR536_SS曲線テ゛ータ.xlsx`＝濁点が分解された表記。
08-11 文書はデスクトップ直下のパスを記載しているが、現物は `Panel\` 配下にある）

### スクリプト
```
D:\Clawdbot_Docker_20260125\scripts\build_inc188_slice3d.py            現行モデルビルダ（最重要）
D:\Clawdbot_Docker_20260125\scripts\build_inc188_2d_planestrain.py     2D平面ひずみ（要素削除せず断念）
D:\Clawdbot_Docker_20260125\scripts\eval_inc188_2d_force_stroke.py     荷重-ストローク評価
D:\Clawdbot_Docker_20260125\scripts\calibrate_mr536_from_ss_curve.py   材料校正
D:\Clawdbot_Docker_20260125\scripts\harvest_shear_blanking_knowledge.py
D:\Clawdbot_Docker_20260125\scripts\refine_shear_blank_mesh.py
D:\Clawdbot_Docker_20260125\scripts\register_inc188_trial_t_growth.py
D:\Clawdbot_Docker_20260125\scripts\ingest_inc188_openradioss_web_knowledge.py
D:\Clawdbot_Docker_20260125\scripts\openradioss_4mmx4mm_assy_params.py DOEパラメータ適用
D:\Clawdbot_Docker_20260125\data\workspace\rad_model.py                RADデック操作
```

### 解析デック
```
D:\Clawdbot_Docker_20260125\data\workspace\openradioss_inc188_trials\INC188_S_S5_0000.rad   最良（成立）
D:\Clawdbot_Docker_20260125\data\workspace\openradioss_inc188_trials\INC188_S_S5_0001.rad
D:\Clawdbot_Docker_20260125\data\workspace\openradioss_inc188_trials\INC188_S_C3|C6|C10|NF_*.rad  校正スイープ
D:\Clawdbot_Docker_20260125\data\workspace\openradioss_inc188_trials\INC188AC_shear_coupon_0000.rad 旧3D最良
```

### 結果
```
D:\Clawdbot_Docker_20260125\clawstack_v2\data\work\INC188_S_*T01.csv    時刻歴（外部仕事→荷重算出元）
D:\Clawdbot_Docker_20260125\clawstack_v2\data\work\INC188_S_*A0??       アニメーション
D:\Clawdbot_Docker_20260125\clawstack_v2\data\work\INC188_S_*_000?.out  ログ
```

### 知識ベース
```
D:\Clawdbot_Docker_20260125\data\workspace\universal_growth.db
   shear_blanking_sources      448件（日本語64件・FTS5 trigram）
   shear_blanking_calibration  実測値と推定値をフラグで区別
   shear_blanking_quarantine   破損1件
```

### 関連文書
```
D:\Clawdbot_Docker_20260125\docs\handover\INC188_SHEAR_BLANKING_HANDOVER_20260811.md  前提（材料・棄却仮説）
D:\Clawdbot_Docker_20260125\data\workspace\memory\trouble_history.md                  T072/T065/T060
D:\Clawdbot_Docker_20260125\docs\cae_north_star_and_meaning_gate_protocol.md          T019
```

---

## 8. 引き継ぎ側への注意

- **数値を引き継ぐ前に出典を確認する。** 本件は出典不明の物理値（580 MPa 等）が一度混入している。
  リポジトリに根拠がない値は使わない。
- **ERR の負値で失敗と判定しない。** 塑性支配モデルでは構造的に負に出る（S5 は -97.0% で正常）。
- **接触ギャップをゼロにしない。** 剪断帯が立たず、工具が板をすり抜ける。
- 記録は `python scripts/record_finding.py` で Beads / Obsidian / auto-memory の3系統へ。
