import json
import urllib.request
import xml.etree.ElementTree as ET
from youtube_transcript_api import YouTubeTranscriptApi
import os
import sys

# Configuration
OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "qwen3:8b"

CHANNELS = [
    {"name": "AI Explained", "id": "UCp_9GybIeJV5CDJ7LlJkFvA"},
    {"name": "Matt Wolfe", "id": "UChpleBmo18P08aKCIgti38g"},
    {"name": "Two Minute Papers", "id": "UCbfYPyITQ-7l4upoX8nvctg"}
]

def call_ollama_summary(transcript_text):
    # Reduced context for speed and reliability
    prompt = f"Summarize the following AI video transcript in 3 Japanese bullet points. Focus on tools/models.\n\nTranscript: {transcript_text[:2000]}"
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(OLLAMA_API_URL, data=data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req, timeout=180) as resp:
            return json.loads(resp.read().decode('utf-8')).get('response', '').strip()
    except:
        return "要約の生成に失敗しました。"

def get_latest_videos(channel_id):
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        with urllib.request.urlopen(rss_url) as resp:
            root = ET.fromstring(resp.read())
            ns = {'yt': 'http://www.youtube.com/xml/schemas/2015', 'atom': 'http://www.w3.org/2005/Atom'}
            entries = []
            for entry in root.findall('atom:entry', ns)[:1]: 
                video_id = entry.find('yt:videoId', ns).text
                title = entry.find('atom:title', ns).text
                entries.append({"id": video_id, "title": title})
            return entries
    except:
        return []

def main():
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass
    
    api = YouTubeTranscriptApi()
    all_results = []
    
    for ch in CHANNELS:
        videos = get_latest_videos(ch['id'])
        for v in videos:
            try:
                transcript_list = api.list(v['id'])
                transcript = transcript_list.find_transcript(['en', 'ja'])
                data = transcript.fetch()
                
                text = ""
                if len(data) > 0:
                    if isinstance(data[0], dict):
                        text = " ".join([t['text'] for t in data])
                    else:
                        text = " ".join([t.text for t in data])
                
                if text:
                    summary = call_ollama_summary(text)
                    all_results.append({
                        "channel": ch['name'],
                        "title": v['title'],
                        "url": f"https://www.youtube.com/watch?v={v['id']}",
                        "summary": summary
                    })
            except:
                continue
    
    print(json.dumps(all_results, ensure_ascii=False))

if __name__ == "__main__":
    main()
