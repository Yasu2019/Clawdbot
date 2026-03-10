import fitz  # PyMuPDF
import sys
import os
import json
import time

PDF_PATH = "/home/node/clawd/fischer.pdf"
INDEX_PATH = "/home/node/clawd/fischer_figure_index.json"
OUTPUT_DIR = "/home/node/clawd/fischer_diagrams_full"

def main():
    if not os.path.exists(INDEX_PATH):
        print(f"Error: Index not found at {INDEX_PATH}. Run index_book_figures.py first.")
        sys.exit(1)
        
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"Created output directory: {OUTPUT_DIR}")

    with open(INDEX_PATH, "r") as f:
        figures = json.load(f)
        
    print(f"Loaded {len(figures)} figures from index.")
    
    doc = fitz.open(PDF_PATH)
    
    total_figures = len(figures)
    
    print(f"Starting Bulk Extraction of {total_figures} figures...")
    
    for i, fig in enumerate(figures):
        # Progress Update for User
        caption = fig['caption']
        page_idx = fig['pdf_page_index']
        
        # Clean caption for filename (e.g., "FIGURE 11.16" -> "Figure_11_16")
        safe_name = caption.replace(" ", "_").replace(".", "_")
        filename = f"{safe_name}_Pg{fig['page']}.png"
        output_path = os.path.join(OUTPUT_DIR, filename)
        
        sys.stdout.write(f"\r[Extracting] {i+1}/{total_figures} : {caption} (Page {fig['page']}) ... ")
        sys.stdout.flush()
        
        if os.path.exists(output_path):
            continue # Skip if already done (resume capability)

        try:
            page = doc.load_page(page_idx)
            # 2x extract for quality
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            pix.save(output_path)
        except Exception as e:
            print(f"Error on {caption}: {e}")
            
    print(f"\n\nBulk Extraction Complete!")
    print(f"Images saved to: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
