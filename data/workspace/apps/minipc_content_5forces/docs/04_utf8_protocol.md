# 04_utf8_protocol - 文字化け防止プロトコル

## 原則

1. ソースコード、Markdown、JSON、YAML、CSVは UTF-8 で保存
2. Windows実行時は `PYTHONUTF8=1`
3. cmd.exeは `chcp 65001`
4. Excelで直接開くCSVは `utf-8-sig` も用意する
5. ファイル名はできるだけ英数字にする
6. 日本語はファイル本文に入れる
7. ZIP生成時はPythonの `zipfile` でUTF-8フラグを使う

## VS Code設定

`.vscode/settings.json`:

```json
{
  "files.encoding": "utf8",
  "files.autoGuessEncoding": false,
  "files.eol": "\n",
  "terminal.integrated.defaultProfile.windows": "PowerShell"
}
```

## PythonでCSV出力する場合

Excelで開く予定がある場合:

```python
df.to_csv("output_excel_safe.csv", encoding="utf-8-sig", index=False)
```

システム間連携の場合:

```python
df.to_csv("output_utf8.csv", encoding="utf-8", index=False)
```
