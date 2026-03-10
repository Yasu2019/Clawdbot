import pypdf
import sys
import os

pdf_path = r"D:\Clawdbot_Docker_20260125\clawstack_v2\data\paperless\consume\Tolerance Analysis\FCI Tolerance Training.pdf"

if not os.path.exists(pdf_path):
    print(f"Error: File not found at {pdf_path}")
    sys.exit(1)

try:
    reader = pypdf.PdfReader(pdf_path)
    print(f"Number of pages: {len(reader.pages)}")
    
    with open("pdf_content.txt", "w", encoding="utf-8") as f:
        for i, page in enumerate(reader.pages):
            f.write(f"\n--- Page {i+1} ---\n")
            text = page.extract_text()
            f.write(text)
    
    print("Full text extracted to pdf_content.txt") 
except Exception as e:
    print(f"Error reading PDF: {e}")
