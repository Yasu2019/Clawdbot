# T055: Cowork(AIサンドボックス)マウント経由のgit/バッチ3重罠 (2026-07-10)

## 症状と回避策(全て実証済み)
1. **index.lockゴースト**: 0バイト残骸がrm後もマウント上に見え続けgit全操作不能
   → 回避: `GIT_INDEX_FILE=/tmp/gidx` + `git read-tree HEAD` で.git/index.lockを一切作らずcommit
2. **git index破損** (bad signature 0x00000000): rm .git/index → git reset で再構築(indexは派生物)
3. **同一ファイルがプロセス毎に別内容**: grepは新版を読みgitは旧版を読む(CHANGELOG.mdで実証)
   → 回避: `git hash-object -w <正しい内容のファイル>` + `git update-index --cacheinfo 100644,<blob>,<path>` でFS迂回
4. **実行中バッチの上書き**: cmdはバイトオフセットで続行→単語途中('th')を誤実行。全ウィンドウ閉→再実行
5. **バッチif内%VAR%未展開**: 旧プロセスkill不発→API孤児多重リスン。kill-by-port方式+遅延展開で根治
6. REMコメントの多バイト文字をcmdが誤解釈→ASCII化

## 教訓
マウント経由のgitは信用しない。書き込み系はplumbing直書きが最終手段。デーモン再起動は「pidファイル信頼」でなく「ポート占有者全掃除」で設計する(T050系統)。

## 追記(同日): 罠7=cp/リダイレクトも切断コピーを拾う
- マウント上の大きめファイル(>11.7KB)はcp先も同一位置で切断され、それをhash-objectすると**切断blobがコミットされる**(CHANGELOG.mdで実発生・同日修復済み)
- 対策: コミット前に必ず `python3 -c "open(f,encoding='utf-8').read()"` でデコード完全性を検証。切断時はホスト側Read/Editツールで全文取得→サンドボックス/tmpに再構築→hash-object
- 履歴上の中間コミット2本(4509bd1/8fba84e)には切断CHANGELOG blobが残存(HEADは修復済み・実害なし)

## 関連: T056(同日採番) — 「プロセス存在=生存」の系統疾患
watchdog 33本が「already running素通り」設計。T050/T051/Moldflow孤児/tri-track4重起動の共通根本原因。設計ルール=①鮮度で死活判定 ②健全な1体の保証(全掃除→単一起動) ③pidファイル単独管理禁止。参照実装3本はT056行参照。
