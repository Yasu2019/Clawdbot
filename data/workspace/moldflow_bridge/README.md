# moldflow_bridge — Moldflow Insight 2010 プログラム制御ブリッジ

北極星(T019)のリファレンスデータ源として、Dynabook上のMoldflow Insight 2010を
GUI(RDP)ではなくCOM API/CLIで制御するための検証・実装フォルダ。

## Step 1: COM接続の最小検証(今ここ)

Dynabookへ `check_synergy_com.vbs` (または .py) をコピーして実行する。

```bat
REM まず64bitで試す
cscript //nologo check_synergy_com.vbs

REM 失敗したら32bit(2010は32bit COMの可能性大)
C:\Windows\SysWOW64\cscript.exe //nologo check_synergy_com.vbs
```

Python版は `pip install pywin32` 後に `python check_synergy_com.py`。

### 判定
- `[OK] CreateObject 成功` → Step 2 へ
- 全ProgID失敗 → Synergy をGUI起動したまま再実行 /
  `reg query HKCR\synergy.Synergy` で登録名を確認して報告

## Step 2(次回): MCPサーバー化の骨子
- Dynabook常駐: Python + FastMCP(HTTP) or 素のHTTP API
- 公開ツール案: new_study / set_material / set_injection_location /
  run_fill_analysis(バッチ `runstudy` 利用・ジョブキュー) / get_results / export_image
- Tailscale (100.98.133.40) 経由で Clawstack / CAE Studio の
  `/api/golden-case` 系へ実測値を供給

## リスクメモ(FMEA抜粋)
| 故障モード | 影響 | 対策 |
|---|---|---|
| 64bit環境からCOM生成不可 | 検証失敗 | SysWOW64 cscript / 32bit Pythonで再試行 |
| ライセンス上バッチ実行不可 | 自動解析不可 | Synergy COM経由の解析実行に切替 |
| 解析中COMブロッキング | ブリッジ応答停止 | ジョブキュー+ポーリング設計(Step 2) |

## ファイル
- `check_synergy_com.vbs` — 依存なしのCOM検証(推奨、まずこちら)
- `check_synergy_com.py` — Python版(pywin32必要、ビット数も表示)

## Step 2A: read-only MCP待受体制

Moldflow未起動でも、MCP通信とCOM事前診断までを準備できる。Dynabook上の管理者
PowerShellで次を実行する。

```powershell
powershell -ExecutionPolicy Bypass -File .\install_dynabook_mcp.ps1
powershell -ExecutionPolicy Bypass -File G:\moldflow_bridge\start_moldflow_mcp.ps1 -Hidden
```

既定endpointは `http://100.98.133.40:8765/mcp`。Windows FirewallはK10の
Tailscale IP `100.119.18.40` だけを許可する。公開ツールは以下のread-only診断のみ。

- `moldflow_bridge_status`
- `moldflow_probe_com` (32/64bit、最大60秒)
- `moldflow_readiness_gate`

K10またはDynabook自身からMCPプロトコルを確認する。

```powershell
G:\moldflow_bridge\.venv\Scripts\python.exe `
  G:\moldflow_bridge\mcp_smoke_client.py `
  --url http://100.98.133.40:8765/mcp
```

`ready_for_analysis` はCOM検証と実API契約確認が終わるまで常にfalse。解析操作を
dry-runや推測APIで代替しない。
