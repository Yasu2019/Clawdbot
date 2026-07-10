from __future__ import annotations

from pathlib import Path
import subprocess
import sys


def build_anomalib_train_command(
    model: str,
    data_root: str | Path,
    category: str,
    output_dir: str | Path,
) -> list[str]:
    """AnomalibのCLIは版で引数が変わるため、実行前に `anomalib --help` を確認してください。

    この関数はコマンドを生成するだけで、外部データの取得や課金API呼出しはしません。
    """
    return [
        sys.executable,
        "-m",
        "anomalib",
        "train",
        "--model",
        model,
        "--data",
        "folder",
        "--data.root",
        str(data_root),
        "--data.name",
        category,
        "--default_root_dir",
        str(output_dir),
    ]


def run_checked(command: list[str]) -> int:
    print("Executing:", " ".join(command))
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise RuntimeError("Anomalibコマンドが失敗しました。導入版のCLIヘルプと引数を確認してください。")
    return completed.returncode
