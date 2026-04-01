# Workstudy Benchmark Setup

1. Workstudy アプリで 1 本動画を解析し、生成された `labels.json` の場所を控えます。
既存プロジェクトがある場合は、まず次で一覧を確認できます。

```powershell
python data\workspace\list_workstudy_projects.py
```
2. 次のコマンドで benchmark 候補を自動生成します。

```powershell
python data\workspace\scaffold_workstudy_benchmark_case.py "D:\path\to\labels.json" --case-id sample_001
```

既存の候補サンプル:
- `data\workspace\workstudy_benchmark_candidate_014babdd.json`

3. 出力された `workstudy_benchmark_candidate.json` を確認し、正解ラベルへ修正します。
4. その内容を `data\workspace\workstudy_benchmark.json` として保存します。
5. 次のコマンドで精度評価を実行します。

```powershell
python data\workspace\evaluate_workstudy_benchmark.py
```

現行の主ラベル:
- `TE`
- `TL`
- `G`
- `RL`
- `P`
- `H`
- `UDe`
- `ADe`
- `I`
- `U`
- `B`
- `UNKNOWN`
