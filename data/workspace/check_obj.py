lines = open(r"D:\Clawdbot_Docker_20260125\data\workspace\ASSY_Guide.obj").readlines()
current_obj = None
stats = {}
for l in lines:
    l = l.strip()
    if l.startswith("o "):
        current_obj = l[2:]
        stats[current_obj] = {"v": 0, "f": 0}
    elif l.startswith("v ") and current_obj:
        stats[current_obj]["v"] += 1
    elif l.startswith("f ") and current_obj:
        stats[current_obj]["f"] += 1

for name, s in stats.items():
    print(f"{name}: {s['v']} vertices, {s['f']} faces")
print(f"\nTotal vertices: {sum(s['v'] for s in stats.values())}")
print(f"Total faces: {sum(s['f'] for s in stats.values())}")
