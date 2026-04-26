import urllib.request
import re
import sys

def get_channel_id(handle):
    url = f"https://www.youtube.com/{handle}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as response:
            html = response.read().decode('utf-8')
            match = re.search(r'"externalId":"([^"]+)"', html)
            if match:
                return match.group(1)
    except Exception as e:
        print(f"Error for {handle}: {e}")
    return None

handles = ["@aiexplained", "@mreflow", "@TwoMinutePapers"]
for h in handles:
    cid = get_channel_id(h)
    print(f"{h}: {cid}")
