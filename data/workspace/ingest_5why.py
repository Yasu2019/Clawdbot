import os
import glob
import pypdf
from pypdf import PdfReader

# Configuration
INPUT_DIR = r"D:\Clawdbot_Docker_20260125\clawstack_v2\data\paperless\consume\5Why_Analysis"
OUTPUT_BASE_DIR = r"D:\Clawdbot_Docker_20260125\data\workspace\consume\5why_wip"

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def process_pdf(pdf_path):
    filename = os.path.basename(pdf_path)
    print(f"Processing: {filename}")
    
    # Create output directory based on filename (without extension)
    safe_name = os.path.splitext(filename)[0].strip()
    target_dir = os.path.join(OUTPUT_BASE_DIR, safe_name)
    ensure_dir(target_dir)
    
    text_out = os.path.join(target_dir, "content.txt")
    img_out_dir = os.path.join(target_dir, "images")
    ensure_dir(img_out_dir)
    
    try:
        reader = PdfReader(pdf_path)
        num_pages = len(reader.pages)
        print(f"  Pages: {num_pages}")
        
        # 1. Text Extraction
        print("  Extracting text...")
        text_content = []
        for i, page in enumerate(reader.pages):
            try:
                txt = page.extract_text()
                if txt:
                    text_content.append(f"\n--- Page {i+1} ---\n{txt}\n")
            except Exception as e:
                print(f"    Page {i+1} text error: {e}")
        
        with open(text_out, "w", encoding="utf-8") as f:
            f.writelines(text_content)
        print(f"  Text saved to {text_out} ({len(text_content)} pages with text)")

        # 2. Image Extraction
        print("  Extracting images...")
        img_count = 0
        for i, page in enumerate(reader.pages):
            try:
                for img in page.images:
                    img_name = f"pg{i+1}_{img.name}"
                    with open(os.path.join(img_out_dir, img_name), "wb") as f:
                        f.write(img.data)
                    img_count += 1
            except Exception as e:
                pass 
        print(f"  Images extracted: {img_count}")
        
    except Exception as e:
        print(f"  CRITICAL ERROR processing {filename}: {e}")

def main():
    pdf_files = glob.glob(os.path.join(INPUT_DIR, "*.pdf"))
    if not pdf_files:
        print("No PDF files found in input directory.")
        return

    print(f"Found {len(pdf_files)} PDFs to process.")
    for pdf in pdf_files:
        process_pdf(pdf)

    print("5Why Ingestion Complete.")

if __name__ == "__main__":
    main()
