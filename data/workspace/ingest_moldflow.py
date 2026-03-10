import os
import pypdf
from pypdf import PdfReader

# Configuration
INPUT_FILES = [
    r"D:\Clawdbot_Docker_20260125\clawstack_v2\data\paperless\consume\Moldflow\Moldflow-反りの発生原理.pdf",
    r"D:\Clawdbot_Docker_20260125\clawstack_v2\data\paperless\consume\Moldflow\リフロー炉内インシュレーター反り変形解析.pdf"
]
OUTPUT_BASE_DIR = r"D:\Clawdbot_Docker_20260125\data\workspace\consume\moldflow_wip"

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Created directory: {path}")

def process_pdf(pdf_path):
    filename = os.path.basename(pdf_path)
    safe_name = os.path.splitext(filename)[0]
    print(f"Processing PDF: {filename}")
    
    if not os.path.exists(pdf_path):
        print(f"Error: PDF file not found at {pdf_path}")
        return

    # Output paths
    pdf_out_dir = os.path.join(OUTPUT_BASE_DIR, safe_name)
    ensure_dir(pdf_out_dir)
    text_out = os.path.join(pdf_out_dir, "content.txt")
    img_out_dir = os.path.join(pdf_out_dir, "images")
    ensure_dir(img_out_dir)
    
    reader = PdfReader(pdf_path)
    print(f"Pages: {len(reader.pages)}")
    
    # 1. Extract Text
    print("Extracting text...")
    full_text = ""
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            full_text += f"\n\n--- Page {i+1} ---\n\n"
            full_text += text
            
    with open(text_out, "w", encoding="utf-8") as f:
        f.write(full_text)
    print(f"Text saved to: {text_out}")
    
    # 2. Extract Images
    print("Extracting images...")
    img_count = 0
    for i, page in enumerate(reader.pages):
        try:
            for image_file_object in page.images:
                try:
                    # Save image
                    # Use index to avoid overwrite if names are generic
                    fname = f"pg{i+1}_{img_count}_{image_file_object.name}"
                    filepath = os.path.join(img_out_dir, fname)
                    
                    with open(filepath, "wb") as fp:
                        fp.write(image_file_object.data)
                    
                    img_count += 1
                except Exception as e:
                    print(f"  Error extracting image on page {i+1}: {e}")
        except Exception as e:
            print(f"  Error processing page {i+1} for images: {e}")
            
    print(f"Extracted {img_count} images to {img_out_dir}")
    print("-" * 40)

def main():
    ensure_dir(OUTPUT_BASE_DIR)
    for pdf in INPUT_FILES:
        process_pdf(pdf)
    print("All processing complete.")

if __name__ == "__main__":
    main()
