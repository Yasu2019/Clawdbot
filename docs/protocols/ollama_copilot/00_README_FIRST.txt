Ollama + GitHub Copilot CLI プロトコル
対象日: 2026-04-20
対象環境: Windows 11 / PowerShell / WSL(Ubuntu) / VS Code

概要
この ZIP は、Ollama から GitHub Copilot CLI を使うための、文字化けしにくい UTF-8(BOM) のテキスト群です。
まずは以下の順で進めてください。

最短ルート
1) Ollama をインストールし、起動確認する
2) GitHub Copilot CLI をインストールする
3) まずは自動セットアップで試す
   ollama launch copilot
4) GitHub 連携も使いたい場合
   copilot login
5) 完全ローカル寄りにしたい場合
   04_OFFLINE_BYOK_LOCAL_ONLY.txt の手順で環境変数を設定してから copilot を起動
6) VS Code 連携したい場合
   03_VSCODE_AND_GITHUB_AUTH.txt を実施

推奨の使い分け
A. とにかく早く試す
   -> 01_WINDOWS_POWERSHELL_SETUP.txt または 02_WSL_BASH_SETUP.txt の「最短起動」

B. ローカルモデルで使いたい
   -> 04_OFFLINE_BYOK_LOCAL_ONLY.txt

C. issue / PR / GitHub 検索も使いたい
   -> GitHub 認証を実施（03_VSCODE_AND_GITHUB_AUTH.txt）

D. 大きめタスクを並列化したい
   -> 05_HEADLESS_AND_FLEET_EXAMPLES.txt の /fleet 例

重要メモ
- BYOK(独自プロバイダ)のみで使う場合、GitHub 認証は必須ではありません。
- ただし、GitHub 認証なしでは /delegate, GitHub MCP server, GitHub Code Search は使えません。
- COPILOT_OFFLINE=true を使うと、GitHub には接続しません。
- ただし、BYOK の接続先がリモート API の場合、その API には通信されます。
- Ollama 側は、Copilot 用途では 64k 以上のコンテキストが推奨です。
- GitHub 側は、tool calling / streaming 対応かつ 128k 程度の文脈長を推奨しています。
  ただし、Ollama 公式の Copilot 連携ページでは 64k 以上を推奨しています。
  実運用では、まず 64k 以上で開始し、重ければモデルや文脈長を調整してください。

同梱ファイル
- 01_WINDOWS_POWERSHELL_SETUP.txt
- 02_WSL_BASH_SETUP.txt
- 03_VSCODE_AND_GITHUB_AUTH.txt
- 04_OFFLINE_BYOK_LOCAL_ONLY.txt
- 05_HEADLESS_AND_FLEET_EXAMPLES.txt
- 06_TROUBLESHOOTING.txt
- run_copilot_local_offline.ps1
- run_copilot_local_offline.sh
