import json

# 1. Fix the 3D model (remove degenerate faces causing red circles)
with open('dp.json', 'r', encoding='utf-8') as f:
    d = json.load(f)

v = d['v']
i = d['i']

pts = [(v[k*3], v[k*3+1], v[k*3+2]) for k in range(len(v)//3)]
faces = [(i[k], i[k+1], i[k+2]) for k in range(0, len(i), 3)]

# The tabs are at Z=1.4 and Z=3.9
# The main block is at Z=13.4 and Z=21.4 (and probably an interface at 3.9)
# The user's screenshot has red circles around the faces connecting the tabs directly to the upper block.
# Let's filter out faces that span a Z distance > 5.0 (e.g. from 1.4 or 3.9 directly up to 13.4).
good_faces = []
for p1, p2, p3 in faces:
    z1, z2, z3 = pts[p1][2], pts[p2][2], pts[p3][2]
    # Check the max Z difference within this face alone
    z_diff = max(z1, z2, z3) - min(z1, z2, z3)
    # 21.4 - 13.4 = 8.0 (this is the legitimate upper block).
    # But a face from 1.4 to 13.4 is 12.0. So z_diff > 10 is a good threshold for the degenerate faces.
    if z_diff < 10.0:
        good_faces.extend([p1, p2, p3])

d['i'] = good_faces

with open('dp_fixed.json', 'w', encoding='utf-8') as f:
    json.dump(d, f)
print(f"Removed {(len(i) - len(good_faces))//3} degenerate faces from the 3D model.")


# 2. Fix the HTML texts (X=Length, Y=Width)
with open('gap_analysis_report.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Replace the 3D model dp json inside
import re
html = re.sub(
    r'(<script\s+type=\"application/json\"\s+id=\"dp\">).*?(</script>)',
    r'\g<1>\n' + json.dumps(d) + r'\n\g<2>',
    html,
    flags=re.DOTALL
)

# Replace the requested texts
html = html.replace('フレーム穴幅 (片側) [D]', 'フレーム長さ (片側) [D]')
html = html.replace('フレーム穴高さ (片側) [D]', 'フレーム幅 (片側) [D]')

html = html.replace('パンチ先端幅 (片側) [A]', 'パンチ先端長さ (片側) [A]')
html = html.replace('パンチ先端高さ (片側) [A]', 'パンチ先端幅 (片側) [A]')

html = html.replace('パンチ先端幅と加工精度エラーが、フレーム穴幅（片側）に対してどのように積み上がるかを計算します。', 'パンチ先端長さと加工精度エラーが、フレーム長さ（片側）に対してどのように積み上がるかを計算します。')
html = html.replace('パンチ先端高さと機械エラー・ガイドあそびが、フレーム穴高さ（片側）に対してどのように積み上がるかを計算します。', 'パンチ先端幅と機械エラー・ガイドあそびが、フレーム幅（片側）に対してどのように積み上がるかを計算します。')

with open('gap_analysis_report.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("Updated HTML with Frame Length and Frame Width labels.")
