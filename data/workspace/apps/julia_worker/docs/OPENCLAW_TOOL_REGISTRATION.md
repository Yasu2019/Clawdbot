# OpenClaw Tool Registration

## 目的

OpenClawからJulia Numerical WorkerをHTTP Toolとして呼び出せるようにします。

## Tool定義例

```json
{
  "name": "julia_leveler_estimate",
  "description": "レベラー条件の簡易推定をJulia Workerで実行する。正式CAEではなく条件探索の初期スクリーニング用。",
  "method": "POST",
  "url": "http://julia-python-bridge:8097/leveler/estimate",
  "input_schema": {
    "type": "object",
    "properties": {
      "thickness_mm": {"type": "number"},
      "yield_mpa": {"type": "number"},
      "roller_diameter_mm": {"type": "number"},
      "pitch_mm": {"type": "number"},
      "entry_gap_mm": {"type": "number"},
      "exit_gap_mm": {"type": "number"},
      "stages": {"type": "integer"},
      "friction": {"type": "number"}
    },
    "required": ["thickness_mm", "yield_mpa", "roller_diameter_mm", "pitch_mm", "entry_gap_mm", "exit_gap_mm"]
  }
}
```

## OpenClawへの指示文

- 結果は「簡易推定」と明記すること。
- 正式な品質判断や条件決定には使わないこと。
- CAEまたは実測確認を次アクションとして提案すること。
- 条件探索の候補出しに使うこと。
