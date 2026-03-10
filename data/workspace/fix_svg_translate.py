import re
import json

with open('dp.json', 'r', encoding='utf-8') as f:
    dp_content = f.read()

with open('gap_analysis_report.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Restore dp.json original geometry
html = re.sub(
    r'(<script\s+type=\"application/json\"\s+id=\"dp\">).*?(</script>)',
    r'\g<1>\n' + dp_content.strip() + r'\n\g<2>',
    html,
    flags=re.DOTALL
)

# 2. X-axis SVG labels translation
html = html.replace('X軸: Worst Case Tolerance Analysis (Min / Max)', 'X軸 スタックアップ')
html = html.replace('Frame Hole Width (片側) [D]', 'フレーム穴幅 (片側) [D]')
html = html.replace('Tool Pos Err [B]', '工具位置誤差 [B]')
html = html.replace('Feed Acc [C]', '送り精度 [C]')
html = html.replace('Pitch Acc [E]', 'ピッチ精度 [E]')
html = html.replace('Minimum Gap (X)', '最小ギャップ (X軸)')
html = html.replace('Maximum Gap (X)', '最大ギャップ (X軸)')

# 3. Y-axis SVG labels translation
html = html.replace('Y軸: Worst Case Tolerance Analysis (Min / Max)', 'Y軸 スタックアップ')
html = html.replace('Frame Hole Height (片側) [D]', 'フレーム穴高さ (片側) [D]')
html = html.replace('Guide Play [C]', 'フレームガイドプレイ (片側) [C]')
html = html.replace('Minimum Gap (Y)', '最小ギャップ (Y軸)')
html = html.replace('Maximum Gap (Y)', '最大ギャップ (Y軸)')

# 'Punch 先端/2 [A]' appears twice in the SVGs. The first one is X-axis (Width), the second is Y-axis (Height).
punch_occurrences = [m.start() for m in re.finditer(re.escape('Punch 先端/2 [A]'), html)]
if len(punch_occurrences) == 2:
    idx1, idx2 = punch_occurrences
    html = html[:idx2] + html[idx2:].replace('Punch 先端/2 [A]', 'パンチ先端高さ (片側) [A]', 1)
    html = html[:idx1] + html[idx1:].replace('Punch 先端/2 [A]', 'パンチ先端幅 (片側) [A]', 1)
elif len(punch_occurrences) > 0:
    print(f"Warning: Found {len(punch_occurrences)} occurrences of 'Punch 先端/2 [A]'. Fixing both to just パンチ先端 (片側) [A]")
    html = html.replace('Punch 先端/2 [A]', 'パンチ先端 (片側) [A]')

with open('gap_analysis_report.html', 'w', encoding='utf-8') as f:
    f.write(html)

print("Successfully reverted 3D geometry and translated SVG labels!")
