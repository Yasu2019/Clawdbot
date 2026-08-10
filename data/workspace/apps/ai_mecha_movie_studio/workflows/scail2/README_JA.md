# SCAIL-2 / ComfyUI連携

1. 既存ComfyUIで動作確認済みSCAIL-2ワークフローを開きます。
2. ComfyUIの「Save (API Format)」でAPI用JSONを書き出します。
3. このフォルダへ `scail2_api.json` として保存します。
4. 入力画像や駆動動画に相当する文字列を、必要なら次のトークンへ置き換えます。

- `{{INPUT_IMAGE}}`
- `{{DRIVING_VIDEO}}`
- `{{OUTPUT_PREFIX}}`

`mecha_studio.adapters.comfyui.submit_api_workflow()` がJSON全体を再帰的に置換してComfyUI `/prompt` へ投入できます。

INT8 / FP8 / GGUFのどれを使うかは既存ComfyUI側のワークフローで選択してください。
このZIPは特定のCustom Node版へ固定しないことで、既存環境との衝突を避けています。
