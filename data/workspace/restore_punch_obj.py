import json
import re

def parse_obj(fp):
    objs = {}
    cur = None
    gv = []
    with open(fp) as f:
        for line in f:
            line = line.strip()
            if not line or line[0] in '#mu': continue
            p = line.split()
            if p[0] == 'o':
                cur = p[1]
                objs[cur] = {'vl': [], 'i': [], 'vo': len(gv)}
            elif p[0] == 'v' and cur:
                c = [float(x) for x in p[1:4]]
                gv.append(c)
                objs[cur]['vl'].extend(c)
            elif p[0] == 'f' and cur:
                poly = []
                for x in p[1:]:
                    idx = int(x.split('/')[0]) - 1
                    poly.append(idx - objs[cur]['vo'])
                for i in range(1, len(poly) - 1):
                    objs[cur]['i'].extend([poly[0], poly[i], poly[i+1]])
    return {n: {'v': d['vl'], 'i': d['i']} for n, d in objs.items()}

if __name__ == '__main__':
    models = parse_obj('ASSY_Guide.obj')
    d_punch = models.get('Punch_for_3D_001', {'v': [], 'i': []})

    with open('gap_analysis_report.html', 'r', encoding='utf-8') as f:
        html = f.read()

    html = re.sub(
        r'(<script\s+type=\"application/json\"\s+id=\"dp\">).*?(</script>)',
        r'\g<1>\n' + json.dumps(d_punch) + r'\n\g<2>',
        html,
        flags=re.DOTALL
    )

    with open('gap_analysis_report.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Successfully restored Punch_for_3D_001 geometry from ASSY_Guide.obj to gap_analysis_report.html")
