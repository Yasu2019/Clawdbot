
import sys
import os

# Try to import PDF libraries
try:
    from pypdf import PdfReader
    print("Using pypdf")
except ImportError:
    try:
        import PyPDF2
        from PyPDF2 import PdfReader
        print("Using PyPDF2")
    except ImportError:
        print("ERROR: No suitable PDF library (pypdf or PyPDF2) found.")
        # Fallback suggestion or exit
        sys.exit(1)

pdf_path = r"D:\Clawdbot_Docker_20260125\clawstack_v2\data\paperless\consume\Guide\エンボス自動機_製品抜きガイド確認_2026-01-27.pdf"

if not os.path.exists(pdf_path):
    print(f"ERROR: File not found at {pdf_path}")
    sys.exit(1)

try:
    reader = PdfReader(pdf_path)
    print(f"--- PDF Meta Info ---")
    print(f"Pages: {len(reader.pages)}")
    if reader.metadata:
        for key, value in reader.metadata.items():
            print(f"{key}: {value}")
    
    print(f"\n--- Content Extraction ---")
    full_text = ""
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        print(f"[Page {i+1}]")
        print(text)
        full_text += text + "\n"
        
    if not full_text.strip():
        print("WARNING: No text extracted. The PDF might be an image scan or contain only vector drawings without text layer.")

except Exception as e:
    print(f"ERROR processing PDF: {e}")
