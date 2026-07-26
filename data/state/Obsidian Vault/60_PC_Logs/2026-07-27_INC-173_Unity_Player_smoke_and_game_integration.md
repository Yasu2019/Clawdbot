# INC-173 Unity Player smoke / 本編段階統合

## QC工程表

| 工程 | 管理項目 | 合格条件 | 結果 |
|---|---|---|---|
| Player Build | compiler/linker | warnings=0, errors=0 | PASS |
| Player Run | 終了コード/JSON | 0 / PASS | PASS |
| Animator | 状態遷移 | Idle>Walking>Talking>Idle | PASS |
| Motion | LeftFoot変化 | 0.1度超または0.0001m超 | 10.3514度 / 0.510514m |
| Test | EditMode | 失敗0 | 4/4 PASS |
| 本編統合 | 必須System参照 | 全て存在 | PASS |
| 保護 | Build Settings | 0件維持 | PASS |

## 5Why / FTA

1. Player固有問題をEditor検証だけでは発見できなかった。
2. Coroutineにcatch付きtry内yieldがありCS1626。
3. Testが製品Assemblyへ混入してNUnit Linker失敗。
4. 初回asmdefは事前定義Assembly-CSharpを参照できなかった。
5. Null graphicsでは描画依存Pose更新が省略され、Smoke Sceneだけ
   AlwaysAnimateが必要だった。

トップ事象は「商用ヒロインを実Playerで証明できない」。要因はCode、
Assembly、Linker、Runtime Culling、Headless Environmentに分解し、各ログで
独立確認した。

## FMEA

| 故障モード | 影響 | RPN | 対策 |
|---|---|---:|---|
| Editorだけで合格 | Player不良流出 | 280 | 実Player JSON+終了コード |
| NUnit混入 | Linker停止 | 84 | Runtime/Test asmdef分離 |
| Poseカリング | 偽FAIL/偽PASS | 192 | Smoke Scene限定AlwaysAnimate |
| Smokeを本編混入 | 自動終了 | 54 | Scene完全分離 |

## 対策結果

Windows PlayerでIdle>Walking>Talking>Idle、LeftFoot 10.3514度/
0.510514m、終了コード0。EditMode 4/4。新規
`TokimekiCommercialGame.unity`にはBootstrap、StateMachine、Dialogue、
Schedule、Stats、LocalLLM、検証済みPrefabを接続した。Build Settingsは空。

## 再利用ルール

IF UnityキャラクターをPlayer-readyとする THEN Editor結果に加えて実Playerの
状態・骨変化・JSON・終了コードを要求する。IF Testがある THEN Runtimeと
Editor Testをasmdefで分離する。

## ロールバック

新規Smoke/Production Scene、PlayerSmoke、2 asmdef、2 Builderと各metaだけを
対象とする。FBX、Prefab、Controller、manifest、Webゲームは対象外。

## Provenance

- Beads: Clawdbot_Docker_20260125-9oie
- Beads memory: unity-packaged-player-gate
- ByteRover: INC-166既知状態でquery/curate各25秒timeout、再試行停止。
- Backup: 35d09d5f245b1b7bc9de8bd993057dda11942ae3
- Log: logs/unity_commercial_heroine_player_build_v6_20260727.log
