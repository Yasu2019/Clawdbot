
import fitz  # PyMuPDF
import os
import glob

INPUT_DIR = "/home/node/clawd/consume/cetol_wip"
OUTPUT_DIR = "/home/node/clawd/consume/cetol_wip/extracted"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

pdf_files = glob.glob(os.path.join(INPUT_DIR, "*.pdf"))
print(f"Found {len(pdf_files)} PDF files in {INPUT_DIR}")

total_extracted = 0

for pdf_path in pdf_files:
    pdf_name = os.path.basename(pdf_path)
    print(f"Processing {pdf_name}...")
    
    try:
        doc = fitz.open(pdf_path)
        print(f"  Pages: {len(doc)}")
        
        for i in range(len(doc)):
            page = doc[i]
            image_list = page.get_images(full=True)
            
            for img_index, img in enumerate(image_list):
                xref = img[0]
                try:
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    ext = base_image["ext"]
                    
                    # Naming convention: PDFName_PgX_ImgY.ext
                    safe_pdf_name = os.path.splitext(pdf_name)[0].replace(" ", "_").replace("-", "_")
                    filename = f"{safe_pdf_name}_pg{i+1}_img{img_index+1}.{ext}"
                    filepath = os.path.join(OUTPUT_DIR, filename)
                    
                    if os.path.exists(filepath):
                        continue

                    # Filter small icons/lines (< 5KB)
                    if len(image_bytes) < 5000:
                        continue
                        
                    with open(filepath, "wb") as f:
                        f.write(image_bytes)
                    total_extracted += 1
                except Exception as e:
                    print(f"  Error on pg{i+1} img{img_index}: {e}")
                    
        print(f"  Finished {pdf_name}")
    except Exception as e:
        print(f"Failed to open {pdf_name}: {e}")

print(f"Total extracted images: {total_extracted}")
