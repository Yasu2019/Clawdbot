# EVO RAM差の調査結果 — 2026-10-18 22:06 JST

Beads: Clawdbot_Docker_20260125-jrth; related resource incident Clawdbot_Docker_20260125-duwz.

## 検証済みの事実

SSHでEVOへ直接照会。DIMM報告合計68,719,476,736B=64GiB、Windows可視33,981,009,920B=31.65GiB、差34,738,466,816B=32.35GiB。現在の表示デバイスAMD Radeon8060SのPNP DeviceIDからDriverキー0001へたどり、HardwareInformation.qwMemorySize=34,359,738,368B=32GiBを確認。0000側の64GiB値は現行表示デバイスの参照先ではなく、判断材料から除外する。Win32_VideoController.AdapterRAMは約4GiBと表示されるが32bit値なので大容量VRAMの根拠にしない。

BIOS: EVO-X2S1.13。BCD全体の照会はexit0、truncatememory/removememory/maxmem/numproc/badmemorylistの明示項目なし。これは全ハードウェア予約がないという意味ではない。

## 原因の判断

32GiBがGPU/UMAに予約されていることがRAM差の主因と強く裏付けられた。残り約0.35GiBはその他予約領域相当だが内訳までは未確認。BIOS画面そのものの現在値は未閲覧であり、ファームウェア設定値を直接読んだと主張しない。

GMKtec公式FAQのEVO-X2 GFX回答は64GB出荷機の初期GFX32GB、BIOSで変更可能と説明。ページHTMLのFAQanswer_jsonを確認。AMD公式はVGMがBIOSレベルでシステムRAMを専用VRAMへ割り当て、CPUから使えるRAMを減らすと説明。実機の32GiB報告と整合する。
Sources accessed2026-10-18:
- https://www.gmktec.com/pages/drivers-and-software
- https://www.amd.com/en/blogs/2025/amd-ryzen-ai-max-personal-ai-supercomputing-guide.html
- https://www.amd.com/en/resources/support-articles/faqs/PA-280.html

## 解消の具体案（未実施）

CPU FEM優先なら保守時にBIOSのGFX Memory/UMA Frame Buffer相当を32GiBから4GiBへ下げる案。搭載BIOSで4GiBが選択可能か実画面で確認し、非対応なら選択肢を記録して再判断する。2GiB等の最小値や正確なメニュー階層は未確認で断定しない。4GiB設定なら約28GiBがCPU側へ戻り、Windows可視は約59.6GiBになる見込みだが再起動後の実測まで確定としない。GPU推論用の固定VRAMは減る。

安全な順序: 現行OpenRadioss2本の所有者・キュー・自動再開タスクとネイティブチェックポイントを検証→計算完了後または回復可能な保守時間にgraceful停止→旧BIOS値を記録してGFX変更→再起動→DIMM/Windows/現行GPU/WSL各層を同時に再実測。WSL memory=20GBは別の制限なので、その後Windows余裕を確保した48GB上限などを検討する。WSL上限変更の反映に必要な停止もチェックポイント保護下で行う。64GiB全量をFEMへ割り当てることはOS/GPU予約のため目標にしない。

本調査ではプロセス/タスク/サービス/ジョブは変更せず、再起動、BIOS/BCD/WSL設定の変更もなし。既存計算を保護。新しいread-only監査スクリプトはEVOで検証済み。

Evidence: D:/Clawdbot_Docker_20260119/artifacts/evo-resource-knowledge-20261018/ram-reservation.json
Probe: scripts/evo_ram_reservation_audit_20261018.ps1