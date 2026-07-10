from __future__ import annotations

import hashlib
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

import yaml

ALLOWED_STATUS={"APPROVED"}


def load_registry(path: str | Path) -> list[dict]:
    with Path(path).open("r",encoding="utf-8") as f: data=yaml.safe_load(f) or {}
    return data.get("datasets",[])


def validate_download_record(record: dict) -> None:
    failures=[]
    if record.get("status") not in ALLOWED_STATUS: failures.append("statusがAPPROVEDではない")
    if record.get("user_approved") is not True: failures.append("ユーザー承認がない")
    if not record.get("sha256") or len(record.get("sha256",""))!=64: failures.append("SHA-256が未設定")
    url=record.get("official_url","")
    parsed=urlparse(url)
    if parsed.scheme not in {"https"}: failures.append("公式HTTPS URLではない")
    if record.get("commercial_use") not in {"YES","ALLOWED"}: failures.append("商用利用可が確認されていない")
    if failures: raise PermissionError("; ".join(failures))


def safe_download(record: dict, destination_dir: str | Path) -> Path:
    validate_download_record(record)
    dest_dir=Path(destination_dir); dest_dir.mkdir(parents=True,exist_ok=True)
    filename=Path(urlparse(record["official_url"]).path).name or f"{record['id']}.bin"
    tmp=dest_dir/(filename+".partial"); final=dest_dir/filename
    h=hashlib.sha256()
    with urllib.request.urlopen(record["official_url"],timeout=60) as response, tmp.open("wb") as f:
        while True:
            chunk=response.read(1024*1024)
            if not chunk: break
            h.update(chunk); f.write(chunk)
    actual=h.hexdigest()
    if actual.lower()!=record["sha256"].lower():
        tmp.unlink(missing_ok=True)
        raise ValueError(f"SHA-256不一致: expected={record['sha256']} actual={actual}")
    tmp.replace(final)
    return final
