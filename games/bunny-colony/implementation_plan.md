# Bunny Colony 採用・実装計画

## 採用判断

**ADOPT_PARTIAL / INTEGRATE**

- `AI_GameDev_Master_2026_Full_Edition_v2.zip` はSteam品質ゲートとPhaser設計を参考にする。
- `BunnyColony_TitleScreen_Complete_v1.0.zip` は世界観、保存、タイトル、Steam抽象化の設計を参考にする。
- 前者のゲームサンプルは構文破損を含み、後者はUnityタイトル画面のみであるため、どちらも原型のまま採用しない。
- 既存 `data/workspace/apps/`、`_legacy/`、`games/` に同等ゲームはない。

## 技術方針

- Electron + HTML5 CanvasによるWindowsデスクトップゲーム
- オフライン完結、外部API・テレメトリなし
- プロシージャル描画のみで第三者アセットの権利問題を回避
- ゲームルールをUIから分離し、Node標準テストで検証
- 新規 `games/bunny-colony/` のみに限定し、Docker・Rails・既存アプリを変更しない

## KPI / 完了条件

| 項目 | 合格条件 |
|---|---|
| プレイ可能性 | タイトル、新規/再開、建築、資源、昼夜、襲撃、勝敗が動作 |
| テスト | ゲームルールの自動テストが全件成功 |
| 配布 | Windows x64実行ファイルまたは展開済みアプリを生成 |
| Steam | depot例、アップロード手順、ストア文案、ライセンス記録を準備 |
| 安全 | 外部通信なし、nodeIntegration無効、CSP設定 |

## ロールバック

`games/bunny-colony/` を除去すれば既存システムへの影響はゼロ。実装前バックアップは `backup/pre-bunny-colony-20260724-041457`。

## No-Go条件

- ビルドまたはルールテストが失敗
- ライセンス不明の素材が混入
- Steam App ID未取得の状態で本番depotへ送信
- 既存Docker/Portal/Railsへの変更が必要になる
