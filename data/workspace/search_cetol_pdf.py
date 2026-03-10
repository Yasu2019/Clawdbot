import pypdf
import os
import glob

# Configuration
SEARCH_DIR = r"D:\Clawdbot_Docker_20260125\clawstack_v2\data\paperless\consume\cetol6sigma"
KEYWORDS = ["System Moment", "システムモーメント", "モーメント法", "Moment Method", "Sensitivity", "感度"]

def search_pdfs():
    pdf_files = glob.glob(os.path.join(SEARCH_DIR, "*.pdf"))
    
    for pdf_path in pdf_files:
        print(f"Scanning: {os.path.basename(pdf_path)}...")
        try:
            reader = pypdf.PdfReader(pdf_path)
            for i, page in enumerate(reader.pages):
                text = page.extract_text()
                if not text:
                    continue
                
                for kw in KEYWORDS:
                    if kw in text or kw.lower() in text.lower():
                        print(f"  [FOUND] '{kw}' in {os.path.basename(pdf_path)} on Page {i+1}")
                        # Print context (a snippet)
                        idx = text.lower().find(kw.lower())
                        start = max(0, idx - 50)
                        end = min(len(text), idx + 100)
                        print(f"    Context: ...{text[start:end].replace(chr(10), ' ')}...")
                        
        except Exception as e:
            print(f"Error reading {pdf_path}: {e}")

if __name__ == "__main__":
    search_pdfs()
