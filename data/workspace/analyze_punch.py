import json
import math

with open('dp.json', 'r') as f:
    d = json.load(f)

v = d['v']
i = d['i']

pts = [(v[k*3], v[k*3+1], v[k*3+2]) for k in range(len(v)//3)]
faces = [(i[k], i[k+1], i[k+2]) for k in range(0, len(i), 3)]

print(f"Total vertices: {len(pts)}")
print(f"Total faces: {len(faces)}")

# Check for degenerate faces
degenerate = 0
for fce in faces:
    p1, p2, p3 = pts[fce[0]], pts[fce[1]], pts[fce[2]]
    a = (p2[0]-p1[0], p2[1]-p1[1], p2[2]-p1[2])
    b = (p3[0]-p1[0], p3[1]-p1[1], p3[2]-p1[2])
    nx = a[1]*b[2] - a[2]*b[1]
    ny = a[2]*b[0] - a[0]*b[2]
    nz = a[0]*b[1] - a[1]*b[0]
    length = math.hypot(nx, ny, nz)
    if length < 1e-4:
        degenerate += 1

print(f"Degenerate faces: {degenerate}")

# Find bounds
xs = [p[0] for p in pts]
ys = [p[1] for p in pts]
zs = [p[2] for p in pts]
print(f"X: {min(xs):.2f} to {max(xs):.2f}")
print(f"Y: {min(ys):.2f} to {max(ys):.2f}")
print(f"Z: {min(zs):.2f} to {max(zs):.2f}")

# Group by Z
z_groups = {}
for pt in pts:
    z = round(pt[2], 2)
    z_groups[z] = z_groups.get(z, 0) + 1
print("Vertices per Z depth:")
for z in sorted(z_groups.keys()):
    print(f"  Z={z}: {z_groups[z]} points")

# Let's see if any points have really weird coordinate values
# Look for points that don't match X/Y pairs across Z
xy_set = set((round(p[0], 2), round(p[1], 2)) for p in pts)
print(f"Unique (X,Y) footprint points: {len(xy_set)}")

for xy in sorted(list(xy_set)):
    # find z for this xy
    z_vals = [round(p[2], 2) for p in pts if round(p[0], 2) == xy[0] and round(p[1], 2) == xy[1]]
    if len(z_vals) % 2 != 0:
        print(f"Odd number of Z values for {xy}: {z_vals} -> potential abnormal geometry!")

