import sys

def parse_full_dxf(filename):
    ents = []
    in_entities_section = False
    with open(filename, 'r', encoding='ansi') as f:
        it = iter(f)
        while True:
            try:
                line = next(it).strip()
                code = line
                value = next(it).strip()
                if code == '0' and value == 'SECTION':
                    if next(it).strip() == '2' and next(it).strip() == 'ENTITIES': in_entities_section = True
                    else: in_entities_section = False
                if in_entities_section:
                    if code == '0':
                        ents.append({'type': value, 'layer': '', 'pts': []})
                    elif ents:
                        if code == '8': ents[-1]['layer'] = value
                        elif code in ['10', '11']: ents[-1]['pts'].append(('x', float(value)))
                        elif code in ['20', '21']: ents[-1]['pts'].append(('y', float(value)))
                if code == '0' and value == 'ENDSEC': in_entities_section = False
            except StopIteration: break
    return [e for e in ents if e['layer'] in ['69', '231']]

ents = parse_full_dxf(r"D:\Clawdbot_Docker_20260125\data\workspace\Punch_Header and Frame_Hole_20260215.dxf")

def get_bbox(pts):
    xs = [p[1] for p in pts if p[0] == 'x']
    ys = [p[1] for p in pts if p[0] == 'y']
    return (min(xs), max(xs), min(ys), max(ys)) if xs and ys else None

shapes = []
for e in ents:
    bbox = get_bbox(e['pts'])
    if not bbox: continue
    found = False
    for s in shapes:
        if e['layer'] != s[0]['layer']: continue
        s_bbox = get_bbox([pt for ent in s for pt in ent['pts']])
        if not (bbox[1] < s_bbox[0]-0.1 or bbox[0] > s_bbox[1]+0.1 or bbox[3] < s_bbox[2]-0.1 or bbox[2] > s_bbox[3]+0.1):
            s.append(e)
            found = True
            break
    if not found: shapes.append([e])

results = {}
for i, s in enumerate(shapes):
    layer = s[0]['layer']
    all_pts = [pt for ent in s for pt in ent['pts']]
    bbox = get_bbox(all_pts)
    w, h = bbox[1]-bbox[0], bbox[3]-bbox[2]
    # Filter for interesting sizes: 0.8, 0.9, 1.0, 2.0, 2.1
    print(f"L:{layer} Shape {i}: W:{w:.4f} H:{h:.4f} at ({bbox[0]:.2f}, {bbox[2]:.2f})")
