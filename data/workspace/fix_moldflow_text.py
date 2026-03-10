import os

INPUT_FILE = r"D:\Clawdbot_Docker_20260125\data\workspace\consume\moldflow_wip\リフロー炉内インシュレーター反り変形解析\content.txt"
OUTPUT_FILE = r"D:\Clawdbot_Docker_20260125\data\workspace\consume\moldflow_wip\リフロー炉内インシュレーター反り変形解析\content_decoded.txt"

def decode_char(c):
    # Keep whitespace and simple formatting
    if c in " \n\r\t":
        return c
    
    # Check for the shift pattern observed: 4 -> S (+31)
    # However, strict +31 might push out of range or into weird chars
    # original '4' is 52. Target 'S' is 83. 52+31=83.
    # original '$' is 36. Target 'C' is 67. 36+31=67.
    # original 'P' is 80. Target 'o' is 111. 80+31=111.
    
    # Apply to basic Latin range roughly
    code = ord(c)
    # Heuristic: if adding 31 results in a valid printable ASCII, do it.
    new_code = code + 31
    if 32 <= new_code <= 126:
        return chr(new_code)
        
    return c # Return original if shift doesn't make sense (e.g. Japanese/Lao chars)

def main():
    if not os.path.exists(INPUT_FILE):
        print("Input file not found.")
        return

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    decoded = []
    for line in content.splitlines():
        decoded_line = "".join([decode_char(c) for c in line])
        decoded.append(decoded_line)

    full_text = "\n".join(decoded)
    
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(full_text)
        
    print(f"Decoded content saved to {OUTPUT_FILE}")
    # Print sample
    print("--- Sample ---")
    print("\n".join(decoded[:20]))

if __name__ == "__main__":
    main()
