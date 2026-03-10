import json
import re

def make_box(xmin, xmax, ymin, ymax, zmin, zmax, v_idx_start):
    v = [
        xmin, ymin, zmax,  xmax, ymin, zmax,  xmax, ymax, zmax,  xmin, ymax, zmax, # top 0,1,2,3
        xmin, ymin, zmin,  xmax, ymin, zmin,  xmax, ymax, zmin,  xmin, ymax, zmin  # bot 4,5,6,7
    ]
    s = v_idx_start
    i = [
         # Top
         s+0, s+1, s+2, s+0, s+2, s+3,
         # Bot
         s+4, s+6, s+5, s+4, s+7, s+6,
         # Front (y min)
         s+0, s+4, s+5, s+0, s+5, s+1,
         # Back (y max)
         s+3, s+2, s+6, s+3, s+6, s+7,
         # Left (x min)
         s+0, s+3, s+7, s+0, s+7, s+4,
         # Right (x max)
         s+1, s+5, s+6, s+1, s+6, s+2
    ]
    return v, i, s + 8

all_v = []
all_i = []
v_idx = 0

# Base body of the punch
v, i, v_idx = make_box(14.54, 33.54, 0.639, 35.639, 3.9, 21.4, v_idx)
all_v.extend(v)
all_i.extend(i)

# The 12 Tabs (The "Tips")
x_ranges = [(15.54, 17.54), (23.04, 25.04), (30.54, 32.54)]
y_ranges = [(7.339, 11.739), (13.739, 18.939), (23.039, 28.239), (30.239, 34.464)]

for xr in x_ranges:
    for yr in y_ranges:
        v, i, v_idx = make_box(xr[0], xr[1], yr[0], yr[1], 1.4, 3.9, v_idx)
        all_v.extend(v)
        all_i.extend(i)

# Save to dp.json
d_punch = {"v": all_v, "i": all_i}
with open('dp_perfect.json', 'w', encoding='utf-8') as f:
    json.dump(d_punch, f)

# Read HTML and inject
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
print("Successfully injected pristine fully-rectangular 3D block geometry for the punch.")
