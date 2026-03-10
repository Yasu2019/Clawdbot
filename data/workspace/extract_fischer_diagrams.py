import fitz  # PyMuPDF
import sys
import os
import time

# Configuration
PDF_PATH = "/home/node/clawd/fischer.pdf"
OUTPUT_DIR = "/home/node/clawd/fischer_diagrams"
TARGET_PAGES = [234, 235, 236]  # 0-indexed, so 235 is 234? Let's extract a range around 235.
# Fischer book Pg 235 usually refers to physical page number. 
# PDF page number might differ. We will extract a few to be sure.

def main():
    if not os.path.exists(PDF_PATH):
        print(f"Error: PDF not found at {PDF_PATH}")
        sys.exit(1)

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Created output directory: {OUTPUT_DIR}")

    print(f"Opening PDF: {os.path.basename(PDF_PATH)}")
    doc = fitz.open(PDF_PATH)
    total_pages = len(doc)
    print(f"Total Pages: {total_pages}")

    # Adjust Logic: If user says Page 235, it's safer to extract 235-1 (0-index) and neighbors.
    # Let's extract 234, 235, 236 (Physical pages 235, 236, 237 roughly)
    # Also PDF page labels might be different.
    
    pages_to_extract = [i for i in range(271, 276)] # Targeting Figures 11.15-11.17 (Detail Drawings)

    print(f"Extracting {len(pages_to_extract)} pages for diagram analysis...")

    for i, page_num in enumerate(pages_to_extract):
        if page_num >= total_pages:
            continue
            
        # Progress Bar Simulation for User Reassurance
        sys.stdout.write(f"\r[Processing] Page {page_num + 1}/{total_pages} ... ")
        sys.stdout.flush()
        
        page = doc.load_page(page_num)
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2)) # 2x zoom for high resolution
        
        output_filename = f"fischer_pg{page_num+1:03d}.png"
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        pix.save(output_path)
        
        # Simulate slight delay if needed or just let it fly. 
        # PyMuPDF is fast, but writing to disk takes ms.
        time.sleep(0.1) 
        
    print(f"\nSuccess! Extracted images to {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
