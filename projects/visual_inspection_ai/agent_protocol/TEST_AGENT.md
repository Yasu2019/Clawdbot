# Test Agent

- unit / integration / regression / performanceを分ける。
- 正常画像だけでなく、ぼけ、暗すぎ、位置ずれ、破損ファイルを試す。
- 評価画像の学習混入を検査する。
- p50/p95/maxとGPU/CPUメモリを記録する。
