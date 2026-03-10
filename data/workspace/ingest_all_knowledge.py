import os
import glob
import pypdf
from pypdf import PdfReader

# Configuration
FISHER_PDF = r"D:\Clawdbot_Docker_20260125\data\workspace\consume\fischer_wip\Fischer_Tolerance_Analysis_2nd.pdf"
CETOL_DIR = r"D:\Clawdbot_Docker_20260125\data\workspace\consume\cetol_wip"
CETOL_PDFS = glob.glob(os.path.join(CETOL_DIR, "*.pdf"))

OUTPUT_BASE_DIR = r"D:\Clawdbot_Docker_20260125\data\workspace\consume"

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def process_pdf(pdf_path, output_subdir_name):
    filename = os.path.basename(pdf_path)
    print(f"Processing: {filename}")
    
    # Output structure: consume/fischer_wip/extracted_v2/
    # or consume/cetol_wip/extracted_v2/{pdf_name}/
    
    base_dir = os.path.dirname(pdf_path)
    target_dir = os.path.join(base_dir, "extracted_full", os.path.splitext(filename)[0])
    ensure_dir(target_dir)
    
    text_out = os.path.join(target_dir, "content.txt")
    img_out_dir = os.path.join(target_dir, "images")
    ensure_dir(img_out_dir)
    
    try:
        reader = PdfReader(pdf_path)
        print(f"  Pages: {len(reader.pages)}")
        
        # 1. Text
        print("  Extracting text...")
        with open(text_out, "w", encoding="utf-8") as f:
            for i, page in enumerate(reader.pages):
                txt = page.extract_text()
                if txt:
                    f.write(f"\n--- Page {i+1} ---\n{txt}\n")
        print(f"  Text saved to {text_out}")

        # 2. Images (Sampling or Full?)
        # For Fisher (500p), full extraction might be huge.
        # But 'pypdf' extracts stream objects.
        print("  Extracting images...")
        img_count = 0
        for i, page in enumerate(reader.pages):
            try:
                for img in page.images:
                    img_name = f"pg{i+1}_{img.name}"
                    with open(os.path.join(img_out_dir, img_name), "wb") as f:
                        f.write(img.data)
                    img_count += 1
            except:
                pass # Skip errors
        print(f"  Images: {img_count}")
        
    except Exception as e:
        print(f"  Error processing {filename}: {e}")

def main():
    # 1. Process Fisher
    if os.path.exists(FISHER_PDF):
        process_pdf(FISHER_PDF, "fischer_wip")
    else:
        print("Fisher PDF not found!")

    # 2. Process Cetol
    print(f"Found {len(CETOL_PDFS)} Cetol PDFs.")
    for pdf in CETOL_PDFS:
        process_pdf(pdf, "cetol_wip")

    print("All Knowledge Ingestion Complete.")

if __name__ == "__main__":
    main()
