
import os
import fitz # PyMuPDF
import re

# Configuration
# PDF located in mounted volume
PDF_PATH = "/home/node/clawd/consume/fischer_wip/Fischer_Tolerance_Analysis_2nd.pdf"
OUTPUT_DIR = "/home/node/clawd/fischer_figures_wip"

if not os.path.exists(OUTPUT_DIR):
    try:
        os.makedirs(OUTPUT_DIR)
    except Exception as e:
        print(f"Error creating dir {OUTPUT_DIR}: {e}")

def extract_figures():
    print(f"Opening {PDF_PATH}...")
    if not os.path.exists(PDF_PATH):
        print(f"Error: PDF not found at {PDF_PATH}")
        return

    try:
        doc = fitz.open(PDF_PATH)
        print(f"Total Pages: {len(doc)}")
        
        count = 0
        # Process all pages
        for i in range(len(doc)):
            page = doc[i]
            image_list = page.get_images(full=True)
            
            # Save images
            for img_index, img in enumerate(image_list):
                xref = img[0]
                try:
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    ext = base_image["ext"]
                    
                    filename = f"pg{i+1}_img{img_index+1}.{ext}"
                    filepath = os.path.join(OUTPUT_DIR, filename)
                    
                    if os.path.exists(filepath):
                        if (i+1) % 50 == 0 and img_index == 0:
                            print(f"Skipping existing page {i+1}...")
                        continue

                    # Filter small icons/lines
                    if len(image_bytes) < 5000: # Skip < 5KB
                        continue
                        
                    with open(filepath, "wb") as f:
                        f.write(image_bytes)
                    count += 1
                except Exception as e:
                    print(f"Error on pg{i+1} img{img_index}: {e}")
                
            if (i+1) % 50 == 0:
                print(f"Processed {i+1} pages...")
                
        print(f"Extracted {count} images to {OUTPUT_DIR}")
    except Exception as e:
        print(f"Exception opening PDF: {e}")

if __name__ == "__main__":
    extract_figures()
