# Moldflow MCP 稼働化 引継ぎ(Fable5 → Codex)

作成: 2026-07-12 Fable5(Cowork)
目的: Dynabook上の実物 Moldflow Insight 2010 を MCPブリッジ(Synergy COM, read-only)で動かし、
K10のCAE Studio(`/api/golden-case`系)へ実機リファレンスを供給する足場を作る(北極星 T019/P025)。

## ゴール(このセッションの完了条件)

1. Dynabookへ到達し、MCPブリッジが起動している
2. K10から `mcp_smoke_client.py` で read-only プローブ(`moldflow_bridge_status` → `moldflow_probe_com`)が成功
3. 結果(COM登録有無・Synergyバージョン・readiness_gate判定)を本文書と同じ`docs/handover/`に追記記録

**やらないこと**: 解析実行(write)は解禁しない(`analysis_enabled=false`のまま)。商用材料カードの複製・転記禁止。「Moldflow同等精度」の主張禁止。

## 現状(2026-07-12時点・全て静的確認済み)

- ブリッジ実体: `D:\Clawdbot_Docker_20260125\data\workspace\moldflow_bridge\`
  - `moldflow_mcp_server.py` (599行, read-only設計, write は環境変数 `MOLDFLOW_ENABLE_WRITE_OPERATIONS=1` が無いと拒否)
  - `install_dynabook_mcp.ps1` / `start_moldflow_mcp.ps1` / `mcp_smoke_client.py` / `test_moldflow_mcp_server.py` / `requirements-mcp.txt`
  - 提供ツール: `moldflow_bridge_status`, `moldflow_probe_com`, `moldflow_inspect_state`, `moldflow_inspect_members`, `moldflow_readiness_gate`
- 実機との通信実績: **ゼロ**(INC-147: :5683プローブtimeout)
- 詳細引継ぎ: `data\workspace\moldflow_bridge\HANDOVER_20260711_moldflow_bridge.md` および
  `HANDOVER_20260711_DYNABOOK_MOLDFLOW_MCP_RETRY.md`(必読)
- 棚卸しマップ: `docs\handover\MOLDFLOW_INVENTORY_AND_MATERIAL_TIERS_FABLE5_20260712.md`

## 対象マシン

| 項目 | 値 |
|---|---|
| ホスト名 | DESKTOP-UOVCG4T (Dynabook) |
| Tailscale IP | 100.98.133.40 |
| ユーザー | mec21 (RDP資格情報はK10のmstscに保存済み) |
| 搭載 | Moldflow Insight 2010 / Tailscale / satelliteワーカー(HTTP :5683, 稼働未確認) |
| 注意 | C:空き約13GBで逼迫。大きな生成物はG:へ |

## 経路の重要制約

- **Cowork(Claude)サンドボックスからTailscale網へは到達不可(検証済)。**
- Codex/CLIエージェントは**K10ホスト上で実行**されるためTailscaleへ到達可能 — 本作業はCodex担当が適切。
- ネットワーク疎通確認は `Test-NetConnection` 禁止(ハーネス20秒制限超過の前科: INC-147)。
  代わりに: `powershell -c "$c=New-Object Net.Sockets.TcpClient; $c.ConnectAsync('100.98.133.40',5683).Wait(5000); $c.Connected"`

## 手順

### STEP 0: 到達確認(K10から、各5秒上限)

```powershell
# ping相当(ICMPはTailscale上で通ることが多い)
powershell -c "(New-Object Net.NetworkInformation.Ping).Send('100.98.133.40',3000).Status"
# ワーカー :5683
powershell -c "$c=New-Object Net.Sockets.TcpClient; $c.ConnectAsync('100.98.133.40',5683).Wait(5000); $c.Connected"
# RDP :3389
powershell -c "$c=New-Object Net.Sockets.TcpClient; $c.ConnectAsync('100.98.133.40',3389).Wait(5000); $c.Connected"
```

全滅の場合: Dynabook本体の電源/Tailscale状態の確認をユーザーへ依頼して終了(推測で先へ進まない)。

### STEP 1: RDP黒画面の修正(未実施の既知修正)

RDPで入れるが黒画面の場合、Dynabook側の管理者PowerShellで(ユーザーに実機操作を依頼するか、
satelliteワーカー経由でコマンド投入できるなら read-only 確認後に):

```powershell
New-Item -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services' -Force | Out-Null
New-ItemProperty -Path 'HKLM:\SOFTWARE\Policies\Microsoft\Windows NT\Terminal Services' -Name fEnableWddmDriver -Value 0 -PropertyType DWord -Force
Restart-Computer -Force
```

注意: RDP接続中にDynabook本体でログインするとセッションが奪われる。

### STEP 2: ブリッジ設置と起動(Dynabook上)

```powershell
# K10からファイル搬入(satelliteワーカーが生きていればそれを利用、なければRDP内でコピー)
# 設置物: data\workspace\moldflow_bridge\ 一式
.\install_dynabook_mcp.ps1     # 依存導入(requirements-mcp.txt)
.\start_moldflow_mcp.ps1       # MCPサーバ起動(read-only)
```

配布時はSHA256照合を必ず行うこと(T051の教訓: 配布はペア+ハッシュ照合。certutilはサービス文脈で
無言失敗するためInvoke-WebRequest/PowerShellのGet-FileHashを使う)。

### STEP 3: スモーク(K10から)

```powershell
cd D:\Clawdbot_Docker_20260125\data\workspace\moldflow_bridge
python mcp_smoke_client.py   # 接続先・ポートは HANDOVER_20260711 参照
```

順序: `moldflow_bridge_status` → `moldflow_probe_com`(COM登録確認) → `moldflow_inspect_state`
→ `moldflow_readiness_gate`。**Synergy COMが未登録の場合**はInsight 2010のインストール状態調査へ
(推測でレジストリをいじらない。まず `inspect_synergy_typelib.py` / `check_synergy_com.vbs` で読取確認)。

### STEP 4: 記録

- 結果(成功/失敗とも)を `docs\handover\` に追記し、`data\workspace\memory\trouble_history.md` に
  新規T番号で登録(最終番号を確認してから採番。2026-07-12時点の最終はT057、ただしT049/T050は
  外観検査AI側で重複使用しているため要注意)。
- bd起票(`bd ready`確認→作業クレーム→完了クローズ→git push まで。セッション完了プロトコル遵守)。

## write(解析実行)解禁の条件(今回はやらない・将来の合意事項)

1. readiness_gate 連続PASS(回数はユーザーと合意)
2. 操作対象を使い捨てstudyファイルに限定(既存プロジェクトへ非破壊)
3. ユーザーの明示承認 — この3点成立時のみ `MOLDFLOW_ENABLE_WRITE_OPERATIONS=1` を付与

## 必読(作業前)

- `data\workspace\memory\trouble_history.md` [T019](北極星・最優先) / [T056](watchdog・「プロセス存在=生存」判定の禁止) / [T051](配布ハッシュ照合)
- `data\workspace\PROMISES.md` P025
- `quality_incident_report_20260711_moldflow_mcp_preflight.md`(INC-147: 前回失敗の教訓)
