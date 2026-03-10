import pypdf
import requests
import json
import os
import time

# Configuration
PDF_PATH = r"D:\Clawdbot_Docker_20260125\clawstack_v2\data\paperless\consume\Tolerance Analysis\Mechanical Tolerance Stackup and Analysis, Second Edition   Bryan R． Fischer 508p_1439815720.pdf"
OUTPUT_MD = r"C:\Users\yasu\.gemini\antigravity\brain\e25395bc-9419-4cc7-a191-c014047344f2\Mechanical_Tolerance_Stackup_Knowledge.md"
MODEL = "deepseek-r1:14b"
OLLAMA_API = "http://localhost:11434/api/generate"
CHUNK_SIZE_PAGES = 5  # Number of pages to process at once

def get_summary(text):
    prompt = f"""
    You are an expert mechanical engineer. Summarize the following text from a book on Tolerance Analysis. 
    Focus on key definitions, formulas, methodologies, and important insights.
    Ignore copyright notices, prefaces, and generic filler.
    Format your response in Markdown points.

    TEXT:
    {text}
    """
    
    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }
    
    try:
        response = requests.post(OLLAMA_API, json=payload)
        response.raise_for_status()
        return response.json().get("response", "")
    except Exception as e:
        print(f"Error calling Ollama: {e}")
        return ""

def main():
    if not os.path.exists(PDF_PATH):
        print(f"PDF not found: {PDF_PATH}")
        return

    reader = pypdf.PdfReader(PDF_PATH)
    total_pages = len(reader.pages)
    print(f"Total Pages: {total_pages}")
    
    with open(OUTPUT_MD, "w", encoding="utf-8") as f:
        f.write("# Mechanical Tolerance Stackup and Analysis - Knowledge Base\n\n")
        f.write(f"**Source:** {os.path.basename(PDF_PATH)}\n")
        f.write(f"**Processed by:** {MODEL}\n\n")

    current_text = ""
    page_count = 0
    
    # Limit processing for demo speed (User can run full later or I can run background)
    # Let's process the first 50 pages and then sampled pages? 
    # Or just sequential. 500 pages -> 100 chunks. 10s per chunk -> 1000s = 16 mins.
    # I should process a TOC and maybe Chapter 1-3 first?
    # Let's try to process a subset first.
    
    import status_reporter
    
    process_pages = range(456, total_pages) # Resume from page 456

    for i in process_pages:
        # Update Status
        status_reporter.update_status("Fischer Text", i+1, total_pages, f"Processing Page {i+1}")
        
        page = reader.pages[i]
        text = page.extract_text()
        if text:
            current_text += text + "\n"
            page_count += 1
        
        if page_count >= CHUNK_SIZE_PAGES:
            print(f"Processing pages {i-page_count+1} to {i+1}...")
            summary = get_summary(current_text)
            
            with open(OUTPUT_MD, "a", encoding="utf-8") as f:
                start_page = (i + 1) - page_count + 1
                end_page = i + 1
                f.write(f"## Section Pages {start_page}-{end_page}\n\n")
                f.write(summary + "\n\n")
            
            current_text = ""
            page_count = 0
            
    # Process remaining
    if current_text:
        print(f"Processing remaining pages...")
        summary = get_summary(current_text)
        with open(OUTPUT_MD, "a", encoding="utf-8") as f:
            f.write(f"## Section Pages {i-page_count+1}-{i+1}\n\n")
            f.write(summary + "\n\n")

    print(f"Knowledge generated at {OUTPUT_MD}")

if __name__ == "__main__":
    main()
