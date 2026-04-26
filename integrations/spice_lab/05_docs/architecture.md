# アーキテクチャ説明

## なぜ二階建て構成にするか

LTspiceはWindows/macOS向け公式アプリとして使うのが最も安定します。一方、Docker内で自動実行・API化・レポート化する用途にはLinuxネイティブのngspiceが適しています。

そのため本パックでは、次の役割分担にします。

```text
Windows LTspice
  - 回路図作成
  - ADIモデル確認
  - 波形ビューアでの目視確認
  - LTspice専用モデルの検証

Docker ngspice
  - 自動解析
  - パラメータスイープ
  - API化
  - OpenClaw連携
  - ログ・CSV・Markdown保存
```

## データフロー

```text
User / OpenClaw
  -> Portal Circuit Simulation Hub
  -> FastAPI /simulate
  -> ngspice -b input.cir
  -> run.log / csv / metadata.json
  -> OpenClaw要約 / RAG投入 / 報告書化
```

## 既存Clawstackへの影響を小さくする設計

- 単体composeで起動可能
- 既定ポートは127.0.0.1:8765
- 既存Gatewayへの変更なしでも使える
- Portalカードは単一HTML
- Gateway tool化は任意
