import re
import json
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(r'd:\Clawdbot_Docker_20260125')
INCIDENT_LOG = REPO_ROOT / 'docs' / 'INCIDENT_LOG.md'
TROUBLE_HISTORY = REPO_ROOT / 'data' / 'workspace' / 'memory' / 'trouble_history.md'
OUTPUT_JSON = REPO_ROOT / 'data' / 'workspace' / 'reliability_metrics.json'

def parse_incidents():
    incidents = []
    
    # Parse INCIDENT_LOG.md
    if INCIDENT_LOG.exists():
        content = INCIDENT_LOG.read_text(encoding='utf-8')
        # Simple regex for INC-XXX
        matches = re.finditer(r'## (INC-\d+): (.*?)\n\| Field \| Detail \|\n\| --- \| --- \|\n\| \*\*Date\*\* \| (.*?) \|', content, re.MULTILINE)
        for m in matches:
            incidents.append({
                'id': m.group(1),
                'title': m.group(2),
                'date': m.group(3),
                'source': 'INCIDENT_LOG'
            })

    # Parse trouble_history.md
    if TROUBLE_HISTORY.exists():
        content = TROUBLE_HISTORY.read_text(encoding='utf-8')
        matches = re.finditer(r'## (\d{4}-\d{2}-\d{2}): (.*?)\n', content)
        for m in matches:
            incidents.append({
                'id': f"TH-{m.group(1)}",
                'title': m.group(2),
                'date': m.group(1),
                'source': 'TROUBLE_HISTORY'
            })
            
    return incidents

def calculate_metrics(incidents):
    if not incidents:
        return {"mtbf_hours": 0, "incident_count": 0, "recent_incidents": []}
    
    # Sort by date
    def parse_date(d_str):
        # Handle formats like "2026-04-25 06:21 JST" or "2026-04-25"
        clean = re.sub(r' JST$', '', d_str).strip()
        try:
            return datetime.strptime(clean, "%Y-%m-%d %H:%M")
        except:
            try:
                return datetime.strptime(clean, "%Y-%m-%d")
            except:
                return datetime.now()

    sorted_inc = sorted(incidents, key=lambda x: parse_date(x['date']))
    
    # Calculate MTBF
    if len(sorted_inc) >= 2:
        total_gap = 0
        for i in range(1, len(sorted_inc)):
            d1 = parse_date(sorted_inc[i-1]['date'])
            d2 = parse_date(sorted_inc[i]['date'])
            gap = (d2 - d1).total_seconds() / 3600.0
            total_gap += gap
        mtbf = total_gap / (len(sorted_inc) - 1)
    else:
        mtbf = 0
        
    return {
        "mtbf_hours": round(mtbf, 1),
        "incident_count": len(incidents),
        "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S JST"),
        "recent_incidents": sorted_inc[-5:][::-1] # Last 5, reversed
    }

def main():
    incidents = parse_incidents()
    metrics = calculate_metrics(incidents)
    
    OUTPUT_JSON.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f"Metrics saved to {OUTPUT_JSON}")

if __name__ == "__main__":
    main()
