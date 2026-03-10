import fitz  # PyMuPDF
import sys
import re
import json

PDF_PATH = "/home/node/clawd/fischer.pdf"

def main():
    print(f"Opening PDF: {PDF_PATH}")
    try:
        doc = fitz.open(PDF_PATH)
    except Exception as e:
        print(f"Error opening PDF: {e}")
        sys.exit(1)

    total_pages = len(doc)
    print(f"Total Pages: {total_pages}")
    
    figures_found = []
    
    # Regex for Figure captions (e.g., "FIGURE 11.16")
    # Case insensitive, looking for Figure followed by numbers
    figure_pattern = re.compile(r"FIGURE\s+\d+\.\d+", re.IGNORECASE)

    print("Scanning for Figures...")
    
    for i in range(total_pages):
        # Progress update every 10 pages or last page
        if i % 10 == 0 or i == total_pages - 1:
            sys.stdout.write(f"\r[Scanning] Page {i+1}/{total_pages} ... Found {len(figures_found)} figures so far.")
            sys.stdout.flush()
            
        page = doc.load_page(i)
        text = page.get_text("text")
        
        matches = figure_pattern.findall(text)
        for match in matches:
            # Simple deduplication per page (sometimes same figure mentioned twice)
            # We treat existence of caption as "This page has a figure definition"
            if match not in [f['caption'] for f in figures_found if f['page'] == i+1]:
               figures_found.append({
                   "page": i+1, # 1-based index for user
                   "pdf_page_index": i,
                   "caption": match
               })

    print(f"\n\nScan Complete.")
    print(f"Total Figures Detected: {len(figures_found)}")
    
    # Save index
    with open("/home/node/clawd/fischer_figure_index.json", "w") as f:
        json.dump(figures_found, f, indent=2)
        
    print("Index saved to fischer_figure_index.json")

if __name__ == "__main__":
    main()
