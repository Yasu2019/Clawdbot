import re, json

html = open(r"D:\Clawdbot_Docker_20260125\data\workspace\gap_analysis_report.html", "r", encoding="utf-8").read()

tags = ["d-guide", "d-frame", "d-strip", "d-punch"]
for tag in tags:
    pattern = f'id="{tag}">'
    idx = html.find(pattern)
    if idx == -1:
        print(f"{tag}: NOT FOUND")
        continue
    start = idx + len(pattern)
    end = html.find("</script>", start)
    data_str = html[start:end]
    try:
        data = json.loads(data_str)
        verts = len(data.get("v", [])) // 3
        faces = len(data.get("i", [])) // 3
        print(f"{tag}: {verts} vertices, {faces} faces")
    except:
        print(f"{tag}: PARSE ERROR (data length: {len(data_str)})")
