# 成形現象動画の分離契約

現象を混ぜた1本の動画は、どの場が何を示すか不明確になるため採用しない。
同一計算のスナップショットを使う場合でも、場と判定結果ごとに別MP4を生成する。

| 動画 | 主フィールド | 判定 |
|---|---|---|
| `fill.mp4` | `alpha.polymer` | 充填フロント・ショートショット |
| `warpage.mp4` | CalculiX変位 `U` | 変形量・拘束条件 |
| `shrinkage_sink.mp4` | PVT体積ひずみ/温度 | 収縮・ヒケ候補 |
| `air_trap.mp4` | 未充填領域 + vent到達 | エアートラップ候補 |
| `weldline.mp4` | 初回到達時刻リッジ/候補場 | ウエルド位置候補 |

レンダラーは場を明示的に選ぶ。

```powershell
py -3 scripts/render_openfoam_vtm_animation.py <VTK_DIR> fill.mp4 `
  --field alpha.polymer --title "Filling"
```

ウエルドライン動画は候補場を生成してから `--field weldline_proxy` で作る。
候補数0は「ウエルドなし」ではなく、フロント合流証拠不足として表示する。
各動画は初期・中間・最終フレームを目視確認し、確認前にTelegramへ送信しない。
