import os

# Target file (ANSYS)
TARGET_FILE = r"D:\Clawdbot_Docker_20260125\data\workspace\consume\fem_cae_wip\ANSYS LS -DYNA10．0 nonlinear finite element analysis HE TAO DENG BIAN ZHU p_7111207521\content.txt"
OUTPUT_FILE = r"D:\Clawdbot_Docker_20260125\data\workspace\consume\fem_cae_wip\ANSYS LS -DYNA10．0 nonlinear finite element analysis HE TAO DENG BIAN ZHU p_7111207521\content_fixed.txt"

def repair_mojibake(text):
    # The text was likely Shift-JIS bytes read as Windows-1252 or Latin-1 by pypdf
    # We need to reverse this: Encode back to bytes (latin1/cp1252), then decode as shift_jis
    
    # Common CP1252 map for the bytes seen:
    # Œ = 0x8C
    # Ž = 0x8E
    # Š = 0x8A
    # • = 0x95
    # etc.
    
    try:
        # Try cp1252 -> shift_jis (Japanese)
        b = text.encode('cp1252')
        decoded = b.decode('shift_jis')
        return decoded
    except Exception as e1:
        try:
            # Fallback to latin1 -> shift_jis
            b = text.encode('latin1')
            decoded = b.decode('shift_jis')
            return decoded
        except Exception as e2:
            return f"[FAILED TO DECODE] {text[:50]}... ({e1})"

def main():
    if not os.path.exists(TARGET_FILE):
        print(f"File not found: {TARGET_FILE}")
        return

    print(f"Reading {TARGET_FILE}...")
    with open(TARGET_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # Process line by line or whole block
    # Whole block might fail if mixed content, so line by line is safer for debugging but slower
    # Let's try whole pages (split by --- Page)
    
    pages = content.split("--- Page")
    fixed_content = []
    
    print(f"Processing {len(pages)} segments...")
    success_count = 0
    
    for p in pages:
        if not p.strip():
            continue
            
        header = "--- Page"
        # The split removes "--- Page", so we add it back conceptually, but wait...
        # "--- Page 1 ---\nTEXT" -> split -> ["", " 1 ---\nTEXT", ...]
        
        # We process the text part.
        # The page number line might be simple ASCII " 1 ---", which survives encoding roundtrip usually.
        
        try:
            # We only repair the text, not the "--- Page X ---" marker if possible, 
            # but actually the marker is ASCII so it should handle roundtrip fine in Shift-JIS too.
            # Let's try fixing the whole chunk.
            
            # Re-attach prefix if it's not the first empty chunk
            chunk = header + p if p else ""
            
            fixed = repair_mojibake(chunk)
            fixed_content.append(fixed)
            success_count += 1
        except:
            # If repair fails, keep original
            fixed_content.append(header + p)

    print(f"Repaired {success_count}/{len(pages)} segments.")
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write("\n".join(fixed_content))
    
    print(f"Saved to {OUTPUT_FILE}")
    
    # Peek at result
    print("--- Preview ---")
    print(fixed_content[1][:500] if len(fixed_content) > 1 else "No content")

if __name__ == "__main__":
    main()
