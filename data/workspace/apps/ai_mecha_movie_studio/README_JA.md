# AI MECHA MOVIE STUDIO V3（全部入り本気版・安全オーケストレーター）

このZIPは、既存のローカルAI環境を**勝手に変更せず**に検出し、ローカルAIモデルへ
「既存システムへ融合する / 単独アプリにする / ハイブリッドにする」の判断を依頼して、
その計画に沿って動画制作パイプラインを組み立てるための実働サンプルです。

## 重要な設計方針

- BAT / PowerShell は一切含みません（過去の誤検知回避）。
- Pythonソース、JSON、MarkdownはUTF-8固定です。
- 起動GUIはPython標準のTkinterなので、コアGUI自体に追加pipは不要です。
- 既存ComfyUI / Blender / FFmpeg / Node / Remotion / Ollama等は「検出して再利用」します。
- AIの判断結果は `workspace/integration_plan.json` に保存します。
- **AIの提案だけで既存環境を書き換えません。** 実行前に人が確認できる設計です。
- 重いAIモデルはZIPへ同梱しません。各公式モデルのライセンスと容量が大きいためです。
- SCAIL-2、Wan2.2、ACE-Step、HunyuanVideo-Foley等は、既存ComfyUIのAPIワークフローを登録して呼び出せます。

## 最初の起動

1. Windowsに Python 3.10～3.13 をインストールしてください。
2. ZIPを展開してください。
3. `START_HERE.py` をダブルクリックしてください。
4. 「1. システム検出」→「2. AIに構成判定を依頼」の順で実行します。
5. Ollamaが動作していれば、検出結果をローカルLLMへ渡して構成を判定します。
6. Ollamaが未起動でも、ルールベースの安全なフォールバック判定が動きます。

## Ollama設定（既定）

- URL: `http://127.0.0.1:11434`
- API: `/api/chat`
- モデル名: GUIで指定可能（例: `qwen3:8b`）

モデルが存在しない場合でもアプリは止まりません。AI判定だけフォールバックへ切り替わります。

## 目標パイプライン

```
FBX / GLB / 画像 / お手本動画 / 音声
        ↓
AI Architecture Planner
  ├─ 既存環境へ融合
  ├─ 単独アプリ
  └─ ハイブリッド
        ↓
[3D精密ルート]
PartCrafter / Hunyuan3D / PartField
→ SkinTokens(TokenRig) / UniRig
→ Puppeteer / Mixamo / GVHMR+GMR
→ Blender Headless

[2D高速ルート]
静止画 + お手本動画
→ SCAIL-2 (ComfyUI)

[音声]
VoxCPM2 / Qwen3-TTS
ACE-Step 1.5
HunyuanVideo-Foley
WhisperX / SenseVoice
DeepFilterNet / ClearerVoice
Audio2Face / MediaPipe / MuseTalk / LatentSync

[最終動画]
Wan2.2 Animate / MiniMax H3(利用可能な場合)
→ Remotion
→ FFmpeg
→ RIFE / Real-ESRGAN
```

## 「そのまま使える」範囲

このZIP単体で次が動きます。

- GUI起動
- Windows/PC環境スキャン
- 既存AIアプリ検出
- Ollamaへ構成判定依頼
- ハイブリッド/統合/単独の計画JSON生成
- サンプルプロジェクト生成
- FFmpegがある場合、疎通確認用の短いMP4生成
- ComfyUI APIのヘルスチェック
- ComfyUI APIワークフローのトークン置換と投入
- Blender Headless用参照画像レンダリングスクリプト
- Remotionテンプレート生成
- UTF-8検査

実際のSCAIL-2等のモデルは、既存ComfyUIへインストール後、ComfyUIから「API Format」で
ワークフローJSONを保存し、`workflows/` 配下へ登録します。

## セキュリティ

- 外部コマンド実行は `subprocess` の引数配列方式を使用し、shell=Trueを使いません。
- AIの返答をコマンドとして直接実行しません。
- 既存システムの削除・上書き・レジストリ変更はしません。
- 自動ダウンロード機能は意図的に付けていません。

## 文字化け対策

`python scripts/verify_utf8.py` を実行すると、ZIP内のテキストファイルをUTF-8として全検査します。
GUI表示を主経路にしているため、Windowsコンソールのコードページ問題も避けやすくしています。
