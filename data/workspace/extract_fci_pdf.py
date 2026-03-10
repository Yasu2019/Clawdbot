import os
import pypdf
from pypdf import PdfReader

# Configuration
INPUT_PDF = r"D:\Clawdbot_Docker_20260125\clawstack_v2\data\paperless\consume\Tolerance Analysis\FCI Tolerance Training.pdf"
OUTPUT_DIR = r"D:\Clawdbot_Docker_20260125\data\workspace\consume\training_wip"
EXTRACTED_IMG_DIR = os.path.join(OUTPUT_DIR, "extracted")
TEXT_OUTPUT = os.path.join(OUTPUT_DIR, "FCI_Tolerance_Training.txt")

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Created directory: {path}")

def main():
    print(f"Processing PDF: {INPUT_PDF}")
    
    if not os.path.exists(INPUT_PDF):
        print(f"Error: PDF file not found at {INPUT_PDF}")
        return

    ensure_dir(OUTPUT_DIR)
    ensure_dir(EXTRACTED_IMG_DIR)
    
    reader = PdfReader(INPUT_PDF)
    print(f"Pages: {len(reader.pages)}")
    
    # 1. Extract Text
    print("Extracting text...")
    full_text = ""
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text:
            full_text += f"\n\n--- Page {i+1} ---\n\n"
            full_text += text
            
    with open(TEXT_OUTPUT, "w", encoding="utf-8") as f:
        f.write(full_text)
    print(f"Text saved to: {TEXT_OUTPUT}")
    
    # 2. Extract Images
    print("Extracting images...")
    img_count = 0
    for i, page in enumerate(reader.pages):
        try:
            for image_file_object in page.images:
                try:
                    # Save image
                    # image_file_object.name usually has extension
                    filename = f"FCI_pg{i+1}_{image_file_object.name}"
                    filepath = os.path.join(EXTRACTED_IMG_DIR, filename)
                    
                    with open(filepath, "wb") as fp:
                        fp.write(image_file_object.data)
                    
                    img_count += 1
                except Exception as e:
                    print(f"  Error extracting image on page {i+1}: {e}")
        except Exception as e:
            print(f"  Error processing page {i+1} for images: {e}")
            
    print(f"Extracted {img_count} images to {EXTRACTED_IMG_DIR}")
    print("Processing Complete.")

if __name__ == "__main__":
    main()
