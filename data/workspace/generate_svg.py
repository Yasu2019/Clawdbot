import sys
import copy

with open('gap_analysis_report.html', 'r', encoding='utf-8') as f:
    html = f.read()

placeholder_html = """<div style="text-align: center; margin: 20px 0; padding: 20px; border: 2px dashed #3498db; background: #f0f8ff;">
<p style="color: #2980b9; font-weight: bold; font-size: 1.2em;">[ ここに1〜2ページのMin/Max分析の図解画像（ユーザー提供）を挿入してください ]</p>
</div>"""

replacement_html = """
<div class="fci-diagrams" style="display: flex; flex-direction: column; gap: 40px; margin: 30px 0;">
    <!-- X-Axis -->
    <div style="border: 1px solid #ccc; padding: 20px; border-radius: 8px; background: #fff; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <h3 style="text-align: center; border-bottom: 2px solid #2980b9; color: #2980b9; padding-bottom: 10px; margin-top: 0;">X軸: Worst Case Tolerance Analysis (Min / Max)</h3>
        <p style="text-align: center; color: #555; margin-bottom: 30px;">パンチ先端幅と加工精度エラーが、フレーム穴幅（片側）に対してどのように積み上がるかを計算します。</p>
        
        <svg width="100%" height="260" viewBox="0 0 800 260" style="font-family: Arial, sans-serif;">
            <!-- Box D -->
            <path d="M 50,180 L 50,230 L 750,230 L 750,180" fill="none" stroke="#2c3e50" stroke-width="3"/>
            <text x="400" y="250" text-anchor="middle" font-size="16" font-weight="bold" fill="#2c3e50">Frame Hole Width (片側) [D]</text>
            <text x="400" y="200" text-anchor="middle" font-size="13" fill="#555">Min: 2.450 &nbsp;&nbsp;&nbsp; Max: 2.550</text>
            
            <!-- Box A -->
            <rect x="90" y="50" width="150" height="50" fill="#1abc9c" stroke="#16a085" stroke-width="2"/>
            <text x="165" y="80" text-anchor="middle" font-size="14" fill="#fff" font-weight="bold">Punch 先端/2 [A]</text>
            <text x="165" y="42" text-anchor="middle" font-size="12" fill="#555">Min: 0.9975</text>
            <text x="165" y="28" text-anchor="middle" font-size="12" fill="#555">Max: 1.0025</text>
            <path d="M 165,105 L 165,150 M 158,142 L 165,154 L 172,142" fill="none" stroke="#1abc9c" stroke-width="4"/>

            <!-- Box B -->
            <rect x="270" y="50" width="130" height="50" fill="#f1c40f" stroke="#f39c12" stroke-width="2"/>
            <text x="335" y="80" text-anchor="middle" font-size="14" fill="#333" font-weight="bold">Tool Pos Err [B]</text>
            <text x="335" y="42" text-anchor="middle" font-size="12" fill="#555">Min: 0.000</text>
            <text x="335" y="28" text-anchor="middle" font-size="12" fill="#555">Max: 0.020</text>
            <path d="M 335,105 L 335,150 M 328,142 L 335,154 L 342,142" fill="none" stroke="#f1c40f" stroke-width="4"/>

            <!-- Box C -->
            <rect x="430" y="50" width="130" height="50" fill="#9b59b6" stroke="#8e44ad" stroke-width="2"/>
            <text x="495" y="80" text-anchor="middle" font-size="14" fill="#fff" font-weight="bold">Feed Acc [C]</text>
            <text x="495" y="42" text-anchor="middle" font-size="12" fill="#555">Min: 0.000</text>
            <text x="495" y="28" text-anchor="middle" font-size="12" fill="#555">Max: 0.011</text>
            <path d="M 495,105 L 495,150 M 488,142 L 495,154 L 502,142" fill="none" stroke="#9b59b6" stroke-width="4"/>

            <!-- Box E -->
            <rect x="590" y="50" width="130" height="50" fill="#e74c3c" stroke="#c0392b" stroke-width="2"/>
            <text x="655" y="80" text-anchor="middle" font-size="14" fill="#fff" font-weight="bold">Pitch Acc [E]</text>
            <text x="655" y="42" text-anchor="middle" font-size="12" fill="#555">Min: 0.000</text>
            <text x="655" y="28" text-anchor="middle" font-size="12" fill="#555">Max: 0.0115</text>
            <path d="M 655,105 L 655,150 M 648,142 L 655,154 L 662,142" fill="none" stroke="#e74c3c" stroke-width="4"/>
        </svg>

        <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; font-size: 15px; line-height: 1.6;">
            <p style="margin: 0;"><strong>Minimum Gap (X)</strong> = D(min) - A(max) - B(max) - C(max) - E(max) <br>
            <span style="display:inline-block; margin-left:135px;">= 2.450 - 1.0025 - 0.020 - 0.011 - 0.0115 = <strong style="color: #e74c3c; font-size: 1.1em;">1.4050 mm</strong></span></p>
            <hr style="border: 0; border-top: 1px dashed #ccc; margin: 10px 0;">
            <p style="margin: 0;"><strong>Maximum Gap (X)</strong> = D(max) - A(min) - B(min) - C(min) - E(min) <br>
            <span style="display:inline-block; margin-left:135px;">= 2.550 - 0.9975 - 0 - 0 - 0 = <strong style="color: #2980b9; font-size: 1.1em;">1.5525 mm</strong></span></p>
        </div>
    </div>
    
    <!-- Y-Axis -->
    <div style="border: 1px solid #ccc; padding: 20px; border-radius: 8px; background: #fff; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
        <h3 style="text-align: center; border-bottom: 2px solid #e67e22; color: #e67e22; padding-bottom: 10px; margin-top: 0;">Y軸: Worst Case Tolerance Analysis (Min / Max)</h3>
        <p style="text-align: center; color: #555; margin-bottom: 30px;">パンチ先端高さと機械エラー・ガイドあそびが、フレーム穴高さ（片側）に対してどのように積み上がるかを計算します。</p>
        
        <svg width="100%" height="260" viewBox="0 0 800 260" style="font-family: Arial, sans-serif;">
            <!-- Box D -->
            <path d="M 80,180 L 80,230 L 720,230 L 720,180" fill="none" stroke="#2c3e50" stroke-width="3"/>
            <text x="400" y="250" text-anchor="middle" font-size="16" font-weight="bold" fill="#2c3e50">Frame Hole Height (片側) [D]</text>
            <text x="400" y="200" text-anchor="middle" font-size="13" fill="#555">Min: 1.000 &nbsp;&nbsp;&nbsp; Max: 1.100</text>
            
            <!-- Box A -->
            <rect x="150" y="50" width="160" height="50" fill="#1abc9c" stroke="#16a085" stroke-width="2"/>
            <text x="230" y="80" text-anchor="middle" font-size="14" fill="#fff" font-weight="bold">Punch 先端/2 [A]</text>
            <text x="230" y="42" text-anchor="middle" font-size="12" fill="#555">Min: 0.5475</text>
            <text x="230" y="28" text-anchor="middle" font-size="12" fill="#555">Max: 0.5525</text>
            <path d="M 230,105 L 230,150 M 223,142 L 230,154 L 237,142" fill="none" stroke="#1abc9c" stroke-width="4"/>

            <!-- Box B -->
            <rect x="340" y="50" width="130" height="50" fill="#f1c40f" stroke="#f39c12" stroke-width="2"/>
            <text x="405" y="80" text-anchor="middle" font-size="14" fill="#333" font-weight="bold">Tool Pos Err [B]</text>
            <text x="405" y="42" text-anchor="middle" font-size="12" fill="#555">Min: 0.000</text>
            <text x="405" y="28" text-anchor="middle" font-size="12" fill="#555">Max: 0.020</text>
            <path d="M 405,105 L 405,150 M 398,142 L 405,154 L 412,142" fill="none" stroke="#f1c40f" stroke-width="4"/>

            <!-- Box C -->
            <rect x="500" y="50" width="140" height="50" fill="#e74c3c" stroke="#c0392b" stroke-width="2"/>
            <text x="570" y="80" text-anchor="middle" font-size="14" fill="#fff" font-weight="bold">Guide Play [C]</text>
            <text x="570" y="42" text-anchor="middle" font-size="12" fill="#555">Min: 0.000</text>
            <text x="570" y="28" text-anchor="middle" font-size="12" fill="#555">Max: 0.100</text>
            <path d="M 570,105 L 570,150 M 563,142 L 570,154 L 577,142" fill="none" stroke="#e74c3c" stroke-width="4"/>
        </svg>

        <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; font-size: 15px; line-height: 1.6;">
            <p style="margin: 0;"><strong>Minimum Gap (Y)</strong> = D(min) - A(max) - B(max) - C(max) <br>
            <span style="display:inline-block; margin-left:135px;">= 1.000 - 0.5525 - 0.020 - 0.100 = <strong style="color: #e74c3c; font-size: 1.1em;">0.3275 mm</strong></span></p>
            <hr style="border: 0; border-top: 1px dashed #ccc; margin: 10px 0;">
            <p style="margin: 0;"><strong>Maximum Gap (Y)</strong> = D(max) - A(min) - B(min) - C(min) <br>
            <span style="display:inline-block; margin-left:135px;">= 1.100 - 0.5475 - 0 - 0 = <strong style="color: #2980b9; font-size: 1.1em;">0.5525 mm</strong></span></p>
        </div>
    </div>
</div>
"""

idx = html.find(placeholder_html)
if idx != -1:
    html = html.replace(placeholder_html, replacement_html)
    with open('gap_analysis_report.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("Successfully injected FCI-styled SVG into HTML.")
else:
    print("Failed to find placeholder in HTML.")
    import re
    m = re.search(r'\[ ここに1〜2ページのMin/Max分析の図解画像（ユーザー提供）を挿入してください \]', html)
    if m:
        print("Found text, but placeholder block did not match exactly.")
    else:
        print("Not found anywhere.")
