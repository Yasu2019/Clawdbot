"""Extract readable text from PDF binary"""
import re, struct

path = r"D:\Clawdbot_Docker_20260125\data\workspace\RB482＊＊制定：ミツイ精密向けN-201品質仕様書(案).pdf"
data = open(path, "rb").read()

# Search for key numeric values in the raw binary
keywords = [b'0.15', b'0.05', b'0.95', b'1.00', b'2.10', b'2.00', b'0.011', b'0.00384', 
            b'0.01152', b'0.020', b'1.5', b'0.6', b'N-201']
print("=== Keyword search in PDF binary ===")
for kw in keywords:
    positions = [m.start() for m in re.finditer(re.escape(kw), data)]
    if positions:
        print(f"  '{kw.decode()}': Found {len(positions)} times at positions {positions[:5]}")
        # Show context around first occurrence
        for pos in positions[:3]:
            start = max(0, pos-30)
            end = min(len(data), pos+30)
            ctx = data[start:end]
            try:
                print(f"    Context: ...{ctx.decode('utf-8', errors='replace')}...")
            except:
                pass
    else:
        print(f"  '{kw.decode()}': NOT found")

# Try to decompress any FlateDecode streams
import zlib
print("\n=== Attempting to decompress PDF streams ===")
stream_starts = [m.start() for m in re.finditer(b'stream\r?\n', data)]
print(f"Found {len(stream_starts)} streams")

all_text = []
for idx, start in enumerate(stream_starts[:20]):
    stream_data_start = data.index(b'\n', start) + 1
    stream_end = data.find(b'\nendstream', stream_data_start)
    if stream_end == -1:
        continue
    raw = data[stream_data_start:stream_end]
    try:
        decompressed = zlib.decompress(raw)
        # Extract text content
        text_matches = re.findall(rb'\(([^)]+)\)', decompressed)
        texts = []
        for t in text_matches:
            try:
                decoded = t.decode('utf-8', errors='ignore')
                if decoded.strip() and len(decoded.strip()) > 0:
                    texts.append(decoded.strip())
            except:
                pass
        if texts:
            print(f"\n  Stream {idx} text: {' '.join(texts[:50])}")
            all_text.extend(texts)
        
        # Also search for numbers
        nums = re.findall(rb'(\d+\.\d+)', decompressed)
        unique_nums = sorted(set(n.decode() for n in nums))
        if unique_nums:
            print(f"  Stream {idx} numbers: {unique_nums[:30]}")
    except:
        pass

print(f"\n=== Total text items extracted: {len(all_text)} ===")
# Print all unique text items
unique_text = sorted(set(all_text))
for t in unique_text[:100]:
    print(f"  {t}")
