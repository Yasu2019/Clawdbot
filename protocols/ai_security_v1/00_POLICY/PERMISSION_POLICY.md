# PERMISSION POLICY

## 原則
AIエージェントには「業務委託者に渡してよい範囲」の権限しか与えない。

## 許可しやすい操作
- RAG検索
- 読み取り専用ファイル参照
- Markdown / CSV / テキスト変換
- ローカル要約・分類

## 原則禁止または要承認
- delete / move / overwrite
- shell execute
- package install
- browser automation with login
- external upload
- secrets access
- firewall or network changes

## 推奨実装
- 読み取り専用ボリューム
- 外部通信 deny by default
- 書き込み先は /sandbox のみ
- 監査ログは /logs に集約
