# Bunny Colony

「Bunny Colony」は、ウサギの集落を育てながら7つの夜を生き延びる、短編コロニー戦略ゲームです。

## プレイ

前提: Node.js 20以上

```powershell
npm install
npm start
```

- 建物ボタン、または `1`～`4` キーで建物を選択
- 草地の空きマスをクリックして建築
- `Esc` で一時停止
- 昼に資源を作り、夜のキツネ襲来に備える
- 7日目の夜を越えると勝利

ゲームは10秒ごと、および建築時に自動保存されます。

## 品質確認とWindowsビルド

```powershell
npm test
npm run build
```

成功すると `release/BunnyColony-1.0.0-Windows-x64.exe` が生成されます。SteamPipe向けには `npm run build:dir` の展開済みフォルダも使用できます。

検証済みリリース:

- ファイル: `release/BunnyColony-1.0.0-Windows-x64.exe`
- サイズ: 89,602,232 bytes (85.45 MiB)
- SHA-256: `AA7305AA52F1DE1F599FECAC098F6DFA3B6A83913255185085CD5935006482CD`
- 検証日: 2026-07-24

## ライセンス

ゲームコードはMIT Licenseです。画像・音声・フォント等の第三者アセットは同梱せず、描画はすべてゲームコード内で生成します。
