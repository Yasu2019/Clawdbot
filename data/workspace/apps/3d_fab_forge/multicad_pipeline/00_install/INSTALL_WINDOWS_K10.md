# Windows 11 / K10 推奨インストール

## 1. Python環境
推奨: Miniconda または venv

```powershell
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install cadquery build123d ocp-vscode numpy pandas pyyaml
```

## 2. FreeCAD
すでにK10に導入済みの場合はそのまま使用。
FreeCAD Pythonは通常Python環境と分離されています。
マクロはFreeCADの「マクロ」から実行するか、FreeCADCmd.exeで実行します。

例:
```powershell
"C:\Program Files\FreeCAD 1.1\bin\FreeCADCmd.exe" 02_examples\freecad\freecad_plate_macro.py
```

## 3. OpenSCAD
OpenSCADをインストールし、openscad.exeにPATHを通す。

## 4. SolveSpace
GUI確認向け。CLI運用は環境依存があるため、まず手動確認用として使う。

## 5. 出力ポリシー
出力は必ず `outputs/` 以下に保存する。
既存ファイルへの上書きは禁止。
