import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any


def atomic_write_json(path: Path, data: Any, backup: bool = True) -> None:
    """
    Writes JSON data to a file atomically using a temporary file and os.replace.
    Optionally creates a .bak backup before overwriting.
    """
    path = Path(path)
    parent = path.parent
    parent.mkdir(parents=True, exist_ok=True)

    # 1. Create a backup if requested and the file exists
    if backup and path.exists():
        bak_path = path.with_suffix(path.suffix + ".bak")
        try:
            shutil.copy2(path, bak_path)
        except Exception:
            pass

    # 2. Write to a temporary file in the same directory to ensure atomic move
    fd, tmp_name = tempfile.mkstemp(dir=parent, prefix=path.name + ".tmp_", suffix=".json", text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        # 3. Replace the original file with the temporary one
        # On Windows, os.replace replaces the destination if it exists.
        os.replace(tmp_name, path)
    except Exception as e:
        # Cleanup temp file on error
        if os.path.exists(tmp_name):
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
        raise e


def safe_load_json(path: Path, fallback: Any) -> Any:
    """
    Loads JSON data from a file, returning fallback if the file is missing,
    empty, or corrupted.
    """
    path = Path(path)
    if not path.exists():
        return fallback
    
    try:
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return fallback
        return json.loads(content)
    except (json.JSONDecodeError, OSError):
        # If corrupted, try loading from .bak if exists
        bak_path = path.with_suffix(path.suffix + ".bak")
        if bak_path.exists():
            try:
                return json.loads(bak_path.read_text(encoding="utf-8"))
            except Exception:
                pass
        return fallback
