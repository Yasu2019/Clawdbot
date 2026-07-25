# -*- coding: utf-8 -*-
import sys
import os
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import time
from pathlib import Path
import requests

def download_file_with_resume(url: str, dest_path: Path, chunk_size: int = 10 * 1024 * 1024):
    """Download a file with Range headers to support resuming."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Get the file size if it already exists
    downloaded_bytes = dest_path.stat().st_size if dest_path.exists() else 0
    
    headers = {}
    if downloaded_bytes > 0:
        headers['Range'] = f"bytes={downloaded_bytes}-"
        print(f"Resuming download from {downloaded_bytes} bytes...", flush=True)

    try:
        response = requests.get(url, headers=headers, stream=True, timeout=30)
        
        # 416 Requested Range Not Satisfiable means we already have the whole file
        if response.status_code == 416:
            print(f"File {dest_path} is already fully downloaded.", flush=True)
            return True
            
        if response.status_code not in (200, 206):
            print(f"Failed to download: HTTP {response.status_code}", flush=True)
            return False

        total_size = int(response.headers.get('content-length', 0)) + downloaded_bytes
        print(f"Total target file size: ~{total_size / (1024*1024):.2f} MB", flush=True)
        
        mode = 'ab' if downloaded_bytes > 0 else 'wb'
        with open(dest_path, mode) as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    f.flush()
                    os.fsync(f.fileno())  # Force write to disk to ensure we don't lose progress on crash
                    downloaded_bytes += len(chunk)
                    sys.stdout.write(f"\rDownloaded: {downloaded_bytes / (1024*1024*1024):.2f} GB / {total_size / (1024*1024*1024):.2f} GB")
                    sys.stdout.flush()
        print("\nDownload finished successfully.", flush=True)
        return True
    except Exception as e:
        print(f"\nDownload interrupted: {e}", flush=True)
        return False

def main() -> int:
    parser = argparse.ArgumentParser(description="Download NVIDIA PartPacker weights safely with resume.")
    parser.add_argument("--repo", default="nvidia/PartPacker")
    parser.add_argument("--file", choices=["vae.pt", "flow.pt"], required=True)
    parser.add_argument("--out-dir", default="E:/AI/PartPacker/pretrained")  # Default to E: to save space on D:
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    
    # Construct Hugging Face raw download URL
    url = f"https://huggingface.co/{args.repo}/resolve/main/{args.file}"
    dest_path = out_dir / args.file
    
    print(f"Target URL: {url}", flush=True)
    print(f"Target Path: {dest_path}", flush=True)
    
    # Retry loop
    max_retries = 50
    for attempt in range(max_retries):
        if download_file_with_resume(url, dest_path):
            print(f"Success! {args.file} downloaded to {dest_path}", flush=True)
            return 0
        print(f"Retrying in 10 seconds... (Attempt {attempt + 1}/{max_retries})", flush=True)
        time.sleep(10)
        
    return 1

if __name__ == "__main__":
    raise SystemExit(main())
