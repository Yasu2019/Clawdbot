# スモークテスト

1. 任意の短いMP4を examples/sample.mp4 として置く
2. 実行
```bash
python scripts/auto_manual_pipeline.py examples/sample.mp4 --out outputs/test --chunk-minutes 1 --frame-interval 5
```
3. outputs/test/manifest.json が生成されること
4. outputs/test/ai_packets/*.json が生成されること
5. OpenCodeGOで prompts/opencodego_main_prompt.md と ai_packets を読み、chunk手順書を作ること
