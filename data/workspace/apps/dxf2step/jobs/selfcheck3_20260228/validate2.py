import Part
from collections import Counter

shape = Part.read('/home/node/clawd/apps/dxf2step/jobs/selfcheck3_20260228/combined.step')
bb = shape.BoundBox

print('=== Validation ===')
print(f'Faces   : {len(shape.Faces)}')
print(f'Solids  : {len(shape.Solids)}')
print(f'Volume  : {shape.Volume:.1f}')
print(f'X span  : {bb.XMax-bb.XMin:.1f}')
print(f'Y span  : {bb.YMax-bb.YMin:.1f}')
print(f'Z span  : {bb.ZMax-bb.ZMin:.1f}')

types = Counter(type(f.Surface).__name__ for f in shape.Faces)
print(f'Face types: {dict(types)}')

is3d = (bb.XMax-bb.XMin) > 0 and (bb.YMax-bb.YMin) > 0 and (bb.ZMax-bb.ZMin) > 0
passed = is3d and shape.Volume > 0 and len(shape.Solids) > 0
print()
print('RESULT:', 'PASS - genuine 3D B-Rep Solid' if passed else 'FAIL')
