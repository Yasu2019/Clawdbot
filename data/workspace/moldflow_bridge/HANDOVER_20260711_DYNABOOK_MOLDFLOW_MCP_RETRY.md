# 引継ぎ: Dynabook Moldflow Insight 2010 MCP再試行

更新日時: 2026-07-11 21:55 JST

## 1. 目的と安全境界

Dynabook上のAutodesk Moldflow Insight 2010 (Synergy)を、K10からTailscale経由の
MCPで段階的に操作可能にする。現段階はread-only事前診断までであり、Study作成、
材料設定、ゲート設定、解析実行は未実装・未許可である。

北極星は実Moldflowによるキャビティ充填リファレンス取得。dry-runや推測COM APIを
解析成功として扱わない。

## 2. Dynabook実機情報

| 項目 | 値 |
|---|---|
| Host | `DESKTOP-UOVCG4T` |
| Tailscale IP | `100.98.133.40` |
| Interactive user | `mec21` |
| Existing worker | `http://100.98.133.40:5683` |
| Moldflow MCP | `http://100.98.133.40:8765/mcp` |
| MCP install root | `G:\moldflow_bridge` |
| Synergy executable | `C:\Program Files\Autodesk\Moldflow Insight 2010\bin\synergy.exe` |
| Synergy version | `09.03.4.0` |
| NLM root | `C:\Program Files (x86)\Autodesk Network License Manager` |
| License file | `C:\Program Files (x86)\Autodesk Network License Manager\license.dat` |

## 3. 完了済み

1. MCP 1.28.1を`G:\moldflow_bridge\.venv`へ導入済み。
2. MCP serverをTailscale address `100.98.133.40:8765`で起動済み。
3. K10からTCP 8765へ到達済み。
4. FastMCPの`421 Invalid Host`を修正済み。
   - DNS rebinding保護は無効化していない。
   - 許可Host/OriginをDynabook Tailscale endpointとlocalhostへ限定。
5. K10からMCP initialize/list-tools成功。
6. 公開ツール:
   - `moldflow_bridge_status`
   - `moldflow_probe_com`
   - `moldflow_readiness_gate`
7. MCP実装commit:
   - `8c7e1711ae` 初期bridge
   - `04a018196c` 非管理者staging対応
   - `17b1601505` Host許可、MCP 1.28.1固定、二重起動防止
8. Synergyは手動で正常起動済み。確認時PID `14756`、`Responding=True`。
9. License server `27000@DESKTOP-UOVCG4T`はUP (MASTER) v11.4。
10. Vendor daemon `adskflex`はUP v11.4。
11. Synergy起動後、feature `77700MFS_2010_0F`を1 license使用していることを確認。

## 4. Licenseバッチの判断

`C:\Users\mec21\Desktop\Autodesk_NLM_Restart.bat`は実在するが、今回は実行しない。
サービスがすでに正常稼働しており、バッチには次の高リスク操作が含まれる。

- 管理者昇格
- Licenseサービスの強制停止
- 停止失敗時のサービスPID/子プロセス強制終了
- License file自動推定
- `lmreread` / `lmstat`

正常稼働中に再起動する利益がなく、停止状態で残るリスクがある。

## 5. 現在のMCPプロセス

Windows venvのため、1サーバーが親子2プロセスとして見える。これは二重サーバーではない。

- venv launcher: PID `12436`
- actual Python: PID `16640`
- parent relation: `16640.ParentProcessId == 12436`
- Uvicorn log: `Uvicorn running on http://100.98.133.40:8765`

PIDは再起動により変わるため、固定値でkillしない。必ずlistenerとCommandLineを再確認する。

## 6. 直近の未完了事項

MCP経由の32bit COM probeを送信したが、K10側の一時Pythonクライアントがcp932で
結果文字列を表示できず、`UnicodeEncodeError`になった。サーバー/MCP通信障害ではなく、
結果表示だけの失敗である。Study作成・解析は行っていない。

根本原因: Windows encoding rule P023をインラインPythonへ適用し忘れた。

## 7. 次回の最優先手順

1. K10側クライアント冒頭で標準出力をUTF-8へ設定する。

```python
import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
```

2. MCP `moldflow_probe_com`を次の引数で1回だけ呼ぶ。

```json
{"bitness": 32, "timeout_sec": 30}
```

3. `[OK] CreateObject`ならProgID、Version、BuildNumber、EditionTypeを記録する。
4. 失敗時だけ64bit probeを1回行う。無制限再試行は禁止。
5. COM契約が実測できるまで解析ツールを推測実装しない。

## 8. 判定基準

### MCP通信PASS

- TCP 8765 reachable
- HTTP通常GETは421ではなく406
- MCP initialize成功
- tools/listで3ツール取得

上記はすべてPASS済み。

### COM PASS

- 32bitまたは64bit VBSで`CreateObject`成功
- Synergyが応答継続
- License server / adskflexがUP継続
- Study/解析の副作用なし

COM結果だけが未確定。

## 8.1 2026-07-11 COM再試行結果

UTF-8出力対策後、MCP tool call自体は成功した。32bit probeはStudy/解析を開始せず
`analysis_started=false`で終了したが、COM生成前にWindows Script Hostの構文エラーとなった。

- 対象: `G:\moldflow_bridge\check_synergy_com.vbs`
- エラー位置: line 30, char 57
- 原因: 旧cscriptがUTF-8日本語文字列を誤解釈
- 対策: VBSのコメントと表示文字列をASCII専用へ変更
- COM成否: 未判定（CreateObject結果ではなくscript parse failure）

## 9. 関連ファイル

- `data/workspace/moldflow_bridge/moldflow_mcp_server.py`
- `data/workspace/moldflow_bridge/mcp_smoke_client.py`
- `data/workspace/moldflow_bridge/check_synergy_com.vbs`
- `data/workspace/moldflow_bridge/start_moldflow_mcp.ps1`
- `data/workspace/moldflow_bridge/install_dynabook_mcp.ps1`
- `data/workspace/moldflow_bridge/README.md`
- `quality_incident_report_20260711_moldflow_mcp_preflight.md`
- `data/state/Obsidian Vault/60_PC_Logs/Moldflow_INC-147_MCP_preflight_20260711.md`

## 10. 禁止事項

- `Autodesk_NLM_Restart.bat`の安易な実行
- License正常時のサービス再起動
- PID未確認の強制終了
- 全LAN向けHost/Origin許可
- DNS rebinding保護の無効化
- COM未確認の解析API実装
- dry-runを実Moldflow成功と表示
- 無制限のCOM/License再試行
