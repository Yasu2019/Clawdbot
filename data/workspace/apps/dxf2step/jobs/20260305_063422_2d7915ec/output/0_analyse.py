import json
import Part
step_path = '/home/node/clawd/apps/dxf2step/jobs/20260305_063422_2d7915ec/output/0.step'
try:
    shape = Part.read(step_path)
    bb    = shape.BoundBox
    result = {
        "volume":  round(shape.Volume, 3),
        "faces":   len(shape.Faces),
        "bbox_x":  round(bb.XMax - bb.XMin, 3),
        "bbox_y":  round(bb.YMax - bb.YMin, 3),
        "bbox_z":  round(bb.ZMax - bb.ZMin, 3),
        "is_valid": shape.isValid(),
        "error":   None,
    }
except Exception as e:
    result = {"volume": 0, "faces": 0, "bbox_x": 0, "bbox_y": 0,
              "bbox_z": 0, "is_valid": False, "error": str(e)}
print(json.dumps(result))
