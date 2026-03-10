
import os
import requests
import json
import io
import base64
# from pdf2image import convert_from_path # Removing dependency
from PIL import Image
import pypdf

# Configuration
PDF_PATH = r"D:\Clawdbot_Docker_20260125\clawstack_v2\data\paperless\consume\Tolerance Analysis\Mechanical Tolerance Stackup and Analysis, Second Edition   Bryan R． Fischer 508p_1439815720.pdf"
OUTPUT_MD = r"C:\Users\yasu\.gemini\antigravity\brain\e25395bc-9419-4cc7-a191-c014047344f2\Mechanical_Tolerance_Stackup_Images.md"
MODEL = "minicpm-v"
OLLAMA_API = "http://127.0.0.1:11434/api/generate"
# DPI = 200 # Resolution for extraction (Not needed for pypdf extraction)
# POPPLER_PATH = ... # Not needed

def encode_image(image):
    buffered = io.BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

def analyze_image(region_img, page_num):
    # Resize if too big
    if region_img.width > 1024 or region_img.height > 1024:
        region_img.thumbnail((1024, 1024))
        
    base64_img = encode_image(region_img)
    
    prompt = """
    You are an expert mechanical engineer analyzing a technical diagram from a Tolerance Analysis book.
    Describe this diagram in detail.
    - Identify if it's a GD&T explanation, a stackup loop, a geometry definition, or a chart.
    - Extract any key formulas, tolerance values, or geometric relationships shown.
    - Explain the "Engineering Intent" of this figure.
    """
    
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "images": [base64_img],
        "stream": False
    }
    
    try:
        response = requests.post(OLLAMA_API, json=payload)
        response.raise_for_status()
        return response.json().get("response", "")
    except Exception as e:
        print(f"Error calling Ollama Vision: {e}")
        return f"failed to analyze: {e}"

def main():
    if not os.path.exists(PDF_PATH):
        print(f"PDF not found: {PDF_PATH}")
        return

    print("Starting Image Analysis (Diagram Reading Mode)...")
    
    # Initialize MD
    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("# Mechanical Tolerance Stackup - Diagram Analysis\n\n")
        f.write(f"**Source:** {os.path.basename(PDF_PATH)}\n")
        f.write(f"**Model:** {MODEL}\n\n")

    # Important pages to check (or range)
    # Checking specific pages first or all? 
    # Generating images is heavy. Let's do a sliding window or key pages.
    # For now, let's process pages 45-55 (Tuning Fork area) and 190-200 (Current Text Area) as a test.
    # Or start from beginning. 
    # Let's try sampling every 5th page or finding pages with images?
    # Better: Scan specific interesting ranges.
    
    import status_reporter
    
    reader = pypdf.PdfReader(PDF_PATH)
    total_pages = len(reader.pages)
    target_pages = range(336, total_pages) 
    
    
    
    try:
        # Use pypdf to extract images directly.
        
        for i in target_pages:
            status_reporter.update_status("Fischer Image (VLM)", i+1, total_pages, f"Scanning Page {i+1}")
            try:
                # Ensure page index is within range
                if i >= len(reader.pages): continue
                
                page = reader.pages[i]
                print(f"Processing Page {i+1}...")
                
                count = 0
                for img_file_obj in page.images:
                    count += 1
                    print(f"  Found image: {img_file_obj.name}")
                    
                    # Convert to PIL
                    img_data = img_file_obj.data
                    image = Image.open(io.BytesIO(img_data))
                    
                    # Skip very small icons/lines
                    if image.width < 100 or image.height < 100:
                        continue
                        
                    analysis = analyze_image(image, i+1)
                    
                    with open(OUTPUT_MD, "a", encoding="utf-8") as f:
                        f.write(f"## Page {i+1} - Diagram {count}\n")
                        f.write(f"![Diagram](data:image/jpeg;base64,skipped)\n\n") 
                        f.write(analysis + "\n\n")
                        f.write("---\n\n")
                        
            except Exception as e:
                print(f"Error on page {i+1}: {e}")

    except Exception as e:
        print(f"Fatal error: {e}")

if __name__ == "__main__":
    main()
