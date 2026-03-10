import re

def extract_models():
    with open('gap_analysis_report.html', 'r', encoding='utf-8') as f:
        html = f.read()
    
    # The custom_logic.js looks for document.getElementById(m.id) where id is 'dp', 'dg', 'df', 'ds'
    # and then calls JSON.parse(el.textContent)
    
    # Try finding elements with id "dp"
    for element_id in ['dp', 'dg', 'df', 'ds']:
        # Regular expression to find <... id="element_id">...</...>
        # This will match generic tags, e.g. <script type="application/json" id="dp">...</script>
        pattern = r'<([a-zA-Z0-9]+)[^>]*?id=[\"\']' + element_id + r'[\"\'][^>]*>(.*?)</\1>'
        matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)
        
        if matches:
            content = matches[0][1]
            print(f"Found {element_id}, length: {len(content)}")
            with open(f'{element_id}.json', 'w', encoding='utf-8') as out:
                out.write(content.strip())
        else:
            print(f"Could not find {element_id}")

if __name__ == '__main__':
    extract_models()
