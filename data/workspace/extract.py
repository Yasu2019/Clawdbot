import re

with open('gap_analysis_report.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Find all script tags
scripts = list(re.finditer(r'<script.*?</script>', content, re.DOTALL))

# The first script is probably three.js minified, the second one might be the custom code
# Let's write the custom scripts to a file
with open('custom_scripts.js', 'w', encoding='utf-8') as f:
    for i, s in enumerate(scripts):
        if len(s.group(0)) < 1000000: # skip the huge three.js
            f.write(f"// Script {i}\n")
            f.write(s.group(0) + "\n\n")

# Remove all scripts for the html body view
body_only = re.sub(r'<script.*?</script>', '', content, flags=re.DOTALL)
with open('body_only.html', 'w', encoding='utf-8') as f:
    f.write(body_only)

print("Extraction complete.")
