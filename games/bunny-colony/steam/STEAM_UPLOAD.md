# Steam公開手順

## 1. Steamworks側で準備

1. Steam DirectでApp Creditを購入し、App IDを取得する。
2. Steamworksの「インストール」タブでWindows 64-bit用Launch Optionを設定する。
3. 1つのWindows depotを作成し、Depot IDを控える。
4. ストアページ、価格、IARC/年齢レーティング、プライバシー情報を入力する。

## 2. リリースビルド

```powershell
cd games\bunny-colony
npm ci
npm run build:dir
```

`release/win-unpacked/` を起動し、以下を実機確認します。

- 新規ゲーム、建築、昼夜、勝敗
- 終了後の再起動とセーブ再開
- 1920x1080、1280x720、1366x768
- オフライン起動
- 30分連続動作

## 3. SteamPipe

`scripts/app_build_steam.vdf.example` と `scripts/depot_build_steam.vdf.example` をコピーし、`APP_ID` / `DEPOT_ID` / `STEAM_CONTENT_ROOT` を実値へ置換します。認証情報はファイルへ保存しません。

```powershell
steamcmd +login YOUR_STEAM_ACCOUNT +run_app_build ..\scripts\app_build_steam.vdf +quit
```

最初は必ず `preview "1"` で確認し、Steamworksの非公開 `default` ブランチでQAを完了してから公開候補へ昇格します。

## 本番公開前に残る外部作業

- App ID / Depot IDの取得
- ストア画像、カプセル、トレーラーの制作
- Steamworks審査
- Steam Deck実機または互換性審査
- 必要に応じたSteamworks SDK統合（実績・クラウドセーブ等）
