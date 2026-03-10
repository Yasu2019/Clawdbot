
import os
import fitz # PyMuPDF
import re

INPUT_DIR = "/home/node/clawd/consume/cetol_wip"
OUTPUT_DIR = os.path.join(INPUT_DIR, "extracted_images")

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def extract_images_from_pdf(pdf_path):
    print(f"Processing {os.path.basename(pdf_path)}...")
    try:
        doc = fitz.open(pdf_path)
        for i in range(len(doc)):
            page = doc[i]
            
            # 1. Extract embedded images
            image_list = page.get_images(full=True)
            
            # If no embedded images, render the whole page (for scanned PDFs or complex layouts)
            # Cetol manuals likely have diagrams mixed with text.
            # Rendering the whole page is safer for context.
            
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # 2x zoom for quality
            
            # Filter: Check if page is mostly empty or just text? 
            # For now, just save every page as an image to be processed by VLM.
            # Filename: PDFName_PageX.png
            
            basename = os.path.splitext(os.path.basename(pdf_path))[0]
            # Sanitize filename
            basename = re.sub(r'[^\w\-_\. ]', '_', basename)
            
            out_name = f"{basename}_pg{i+1}.png"
            out_path = os.path.join(OUTPUT_DIR, out_name)
            
            pix.save(out_path)
            
            if (i+1) % 5 == 0:
                print(f"  Saved page {i+1}")

        print(f"  -> Extracted {len(doc)} pages.")
    except Exception as e:
        print(f"  -> Error: {e}")

def main():
    files = [f for f in os.listdir(INPUT_DIR) if f.lower().endswith(".pdf")]
    print(f"Found {len(files)} PDFs.")
    
    for f in files:
        extract_images_from_pdf(os.path.join(INPUT_DIR, f))

if __name__ == "__main__":
    main()
