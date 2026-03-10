import sys

def extract_dxf_metadata(filename):
    metadata = {'text': [], 'dims': []}
    with open(filename, 'r', encoding='ansi') as f:
        it = iter(f)
        while True:
            try:
                line = next(it).strip()
                code = line
                value = next(it).strip()
                
                if code == '1': # Primary text string
                    metadata['text'].append(value)
                elif code == '42': # Actual measurement (Dimensions)
                    metadata['dims'].append(value)
                    
            except StopIteration:
                break
    return metadata

data = extract_dxf_metadata(r"D:\Clawdbot_Docker_20260125\data\workspace\Punch_Header and Frame_Hole_20260215.dxf")

print("--- TEXT STRINGS ---")
for t in sorted(list(set(data['text']))):
    print(t)

print("\n--- DIMENSION VALUES ---")
for d in sorted(list(set(data['dims']))):
    print(d)
