import Part

step = '/home/node/clawd/apps/dxf2step/jobs/selfcheck_20260228/combined.step'
shape = Part.read(step)
bb = shape.BoundBox

xspan = bb.XMax - bb.XMin
yspan = bb.YMax - bb.YMin
zspan = bb.ZMax - bb.ZMin

print("=== combined.step Validation ===")
print(f"Volume   : {shape.Volume:.3f}")
print(f"X span   : {xspan:.3f}  ({bb.XMin:.1f} to {bb.XMax:.1f})")
print(f"Y span   : {yspan:.3f}  ({bb.YMin:.1f} to {bb.YMax:.1f})")
print(f"Z span   : {zspan:.3f}  ({bb.ZMin:.1f} to {bb.ZMax:.1f})")
print(f"Faces    : {len(shape.Faces)}")
print(f"Solids   : {len(shape.Solids)}")
print()

is_3d = xspan > 0 and yspan > 0 and zspan > 0
has_volume = shape.Volume > 0
is_solid = len(shape.Solids) > 0

print("=== Self-check result ===")
print(f"[{'PASS' if is_3d else 'FAIL'}] 3D (all axes have extent)")
print(f"[{'PASS' if has_volume else 'FAIL'}] Volume > 0")
print(f"[{'PASS' if is_solid else 'FAIL'}] Contains solid(s)")
print()
if is_3d and has_volume and is_solid:
    print(">> RESULT: PASS - genuine 3D solid reconstructed")
else:
    print(">> RESULT: FAIL - shape is flat or empty")
