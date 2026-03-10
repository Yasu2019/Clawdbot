import traceback

html = open('gap_analysis_report_fixed.html', encoding='utf-8').read()
idx = html.find('<!-- SECTION 1: WORST CASE -->')

if idx != -1:
    minmax = '''
<!-- SECTION 1.5: MIN/MAX EXPLANATION -->
<h2 class="stitle">Min/Max分析（最悪ケース分析）の視覚的解説</h2>
<div class="ib">
<h4>&#x1F4A1; Min/Max分析とは？</h4>
<p>Min/Max分析（最悪ケース分析）は、製造における各部品の寸法公差がすべて「最も不利な方向」に極端に振れた場合を想定し、それでも干渉や隙間不足が発生しないかを確認する手法です。</p>
<p><b>■ ユーザー指定の図解：</b></p>
<ul>
<li>構成部品の最大寸法 (Max) と 最小寸法 (Min) を図面から抽出し、積み上げ（スタックアップ）を行います。</li>
<li>本レポートでは、パンチ先端（最大）とフレーム穴（最小）の最悪の組み合わせにおけるギャップを計算しています。</li>
</ul>
<div style="text-align: center; margin: 20px 0; padding: 20px; border: 2px dashed #3498db; background: #f0f8ff;">
<p style="color: #2980b9; font-weight: bold; font-size: 1.2em;">[ ここに1〜2ページのMin/Max分析の図解画像（ユーザー提供）を挿入してください ]</p>
</div>
</div>

'''
    html = html[:idx] + minmax + html[idx:]
    open('gap_analysis_report.html', 'w', encoding='utf-8').write(html)
    print('Injected UI explanation successfully!')
else:
    print('Could not find injection point.')
