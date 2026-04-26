# LTspice GUIをDocker内で常用しない理由

## 理由

1. LTspiceは公式にはWindows/macOS向け配布が中心です。
2. Linux Docker内で動かす場合、WineやX11/VNCが必要になり、GUI・フォント・ファイルパス・波形表示が不安定になりがちです。
3. 鈴木様の目的はGUI操作そのものではなく、OpenClawから自動解析・レポート化できることです。
4. Docker内の自動解析はngspiceの方が保守しやすいです。

## 例外

以下の場合だけ、LTspiceバッチ連携を検討します。

- ADI専用モデルをそのまま使いたい
- LTspiceでしか再現できない回路がある
- 既存の `.asc` / `.asy` / `.lib` 資産が多い

その場合も、推奨は「WindowsホストのLTspiceをPowerShell経由でバッチ実行」です。
