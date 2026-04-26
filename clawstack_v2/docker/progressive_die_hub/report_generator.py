"""
report_generator.py — HTML 設計報告書生成
"""
from datetime import datetime
from typing import Dict, Any


TEMPLATE = """\
<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>順送金型 設計報告書</title>
<style>
  body{font-family:'Segoe UI',sans-serif;background:#0f0f1a;color:#e0e0e0;margin:0;padding:20px;}
  h1{color:#4fc3f7;border-bottom:2px solid #4fc3f7;padding-bottom:8px;}
  h2{color:#81d4fa;border-left:4px solid #4fc3f7;padding-left:10px;margin-top:30px;}
  h3{color:#b3e5fc;}
  .meta{color:#aaa;font-size:.9em;margin-bottom:20px;}
  table{border-collapse:collapse;width:100%;margin:12px 0;}
  th{background:#1e3a5f;color:#b3e5fc;padding:8px 12px;text-align:left;border:1px solid #2a4a7f;}
  td{padding:7px 12px;border:1px solid #2a4a7f;vertical-align:top;}
  tr:nth-child(even)td{background:#161630;}
  .ok{color:#66bb6a;font-weight:bold;}
  .warn{color:#ffa726;font-weight:bold;}
  .badge{display:inline-block;padding:2px 8px;border-radius:4px;font-size:.85em;}
  .badge-ok{background:#1b5e20;color:#a5d6a7;}
  .badge-warn{background:#e65100;color:#ffccbc;}
  .section{background:#12122a;border:1px solid #2a4a7f;border-radius:6px;padding:16px;margin:16px 0;}
  .svg-wrap{overflow-x:auto;background:#1a1a2e;padding:10px;border-radius:6px;margin:10px 0;}
  .kv{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:8px;margin:10px 0;}
  .kv-item{background:#1e2040;border:1px solid #334;border-radius:4px;padding:8px 12px;}
  .kv-label{color:#888;font-size:.8em;}
  .kv-value{color:#e0e0e0;font-size:1.1em;font-weight:bold;}
  .station-op-pilot_hole{color:#FFE66D;}
  .station-op-notch{color:#FF6B6B;}
  .station-op-hole_punch{color:#FFE66D;}
  .station-op-bend{color:#4ECDC4;}
  .station-op-cutoff{color:#66bb6a;}
  pre{background:#0d1117;padding:12px;border-radius:4px;overflow-x:auto;font-size:.82em;color:#c9d1d9;}
  .footer{color:#555;font-size:.8em;margin-top:40px;border-top:1px solid #333;padding-top:10px;}
</style>
</head>
<body>
<h1>📋 順送金型 設計報告書</h1>
<div class="meta">生成日時: {timestamp} | ファイル: {filename}</div>

<h2>1. 部品ジオメトリ</h2>
<div class="section">
<div class="kv">
  <div class="kv-item"><div class="kv-label">外形幅</div><div class="kv-value">{part_w:.2f} mm</div></div>
  <div class="kv-item"><div class="kv-label">外形高さ</div><div class="kv-value">{part_h:.2f} mm</div></div>
  <div class="kv-item"><div class="kv-label">板厚</div><div class="kv-value">{thickness:.2f} mm</div></div>
  <div class="kv-item"><div class="kv-label">材料</div><div class="kv-value">{mat_name}</div></div>
  <div class="kv-item"><div class="kv-label">穴数</div><div class="kv-value">{hole_count} 個</div></div>
  <div class="kv-item"><div class="kv-label">曲げ箇所</div><div class="kv-value">{bend_count} 箇所</div></div>
</div>
</div>

<h2>2. ブランク展開寸法</h2>
<div class="section">
<div class="kv">
  <div class="kv-item"><div class="kv-label">展開幅</div><div class="kv-value">{flat_w:.2f} mm</div></div>
  <div class="kv-item"><div class="kv-label">展開高さ</div><div class="kv-value">{flat_h:.2f} mm</div></div>
  <div class="kv-item"><div class="kv-label">曲げ代合計</div><div class="kv-value">{total_ba:.3f} mm</div></div>
  <div class="kv-item"><div class="kv-label">K 係数</div><div class="kv-value">{k_factor:.2f}</div></div>
</div>
</div>

<h2>3. ストリップレイアウト</h2>
<div class="section">
<div class="kv">
  <div class="kv-item"><div class="kv-label">工程数</div><div class="kv-value">{station_count}</div></div>
  <div class="kv-item"><div class="kv-label">送りピッチ</div><div class="kv-value">{pitch:.2f} mm</div></div>
  <div class="kv-item"><div class="kv-label">ストリップ幅</div><div class="kv-value">{strip_w:.2f} mm</div></div>
  <div class="kv-item"><div class="kv-label">必要プレス容量</div><div class="kv-value">{press_ton:.0f} ton</div></div>
</div>
<div class="svg-wrap">
{svg_content}
</div>
<h3>工程詳細</h3>
<table>
<tr><th>No.</th><th>工程名</th><th>操作</th><th>打ち抜き力</th><th>詳細</th></tr>
{station_rows}
</table>
</div>

<h2>4. FEM 解析（OpenRadioss）</h2>
<div class="section">
{radioss_section}
</div>

<h2>5. パンチ・ダイ強度（CalculiX）</h2>
<div class="section">
{calculix_section}
</div>

<h2>6. 設計サマリー・判定</h2>
<div class="section">
{summary_section}
</div>

<div class="footer">
本報告書は Clawstack Progressive Die Hub により自動生成されました。<br>
FEM 解析結果は参考値です。量産前に必ず実機確認を行ってください。
</div>
</body>
</html>
"""


def _station_op_label(op: str) -> str:
    labels = {
        'pilot_hole': 'パイロット穴',
        'notch':      'ノッチング',
        'hole_punch': '内穴打ち抜き',
        'bend':       '曲げ',
        'cutoff':     '切り落とし',
    }
    return labels.get(op, op)


def generate(
    geom: Dict,
    layout: Dict,
    fem_blanking: Dict,
    fem_bending:  Dict,
    calc_punch:   Dict,
    calc_die:     Dict,
    params: Dict,
) -> str:
    mat     = layout['material']
    blank   = layout['blank']
    summary = layout['summary']
    dims    = geom['dimensions']

    # 工程行
    rows = ''
    for st in layout['stations']:
        op_cls = f"station-op-{st['operation']}"
        rows += (f'<tr><td>{st["no"]}</td>'
                 f'<td><span class="{op_cls}">{st["name"]}</span></td>'
                 f'<td>{_station_op_label(st["operation"])}</td>'
                 f'<td>{st["punch_force"]} kN</td>'
                 f'<td>{st["description"]}</td></tr>\n')

    # OpenRadioss セクション
    if fem_blanking and fem_bending:
        b_info = fem_blanking.get('info', {})
        v_info = fem_bending.get('info', {})
        radioss_sec = f"""
<div class="kv">
  <div class="kv-item"><div class="kv-label">打ち抜き解析 要素数</div>
    <div class="kv-value">{b_info.get('element_count', '-')}</div></div>
  <div class="kv-item"><div class="kv-label">打ち抜き力</div>
    <div class="kv-value">{b_info.get('punch_force_kN', '-')} kN</div></div>
  <div class="kv-item"><div class="kv-label">クリアランス（片側）</div>
    <div class="kv-value">{b_info.get('clearance_mm', '-')} mm</div></div>
  <div class="kv-item"><div class="kv-label">曲げ解析 要素数</div>
    <div class="kv-value">{v_info.get('element_count', '-')}</div></div>
  <div class="kv-item"><div class="kv-label">スプリングバック推定</div>
    <div class="kv-value">{v_info.get('springback_deg', '-')}°</div></div>
  <div class="kv-item"><div class="kv-label">補正曲げ角度</div>
    <div class="kv-value">{v_info.get('corrected_angle', '-')}°</div></div>
</div>
<p style="color:#aaa;font-size:.9em;">
入力デッキ（blanking_starter.rad, bending_starter.rad）をダウンロードして
OpenRadioss コンテナで実行してください：<br>
<code>docker exec clawstack-unified-openradioss-1 bash -c
"cd /work && openradioss -nt 4 blanking_starter bending_starter"</code>
</p>
"""
    else:
        radioss_sec = '<p>FEM 入力デッキを生成するには「FEM 解析」タブを実行してください。</p>'

    # CalculiX セクション
    if calc_punch:
        st_punch = '<span class="badge badge-ok">OK</span>' \
            if calc_punch.get('status') == 'OK' \
            else '<span class="badge badge-warn">要確認</span>'
        st_die = '<span class="badge badge-ok">OK</span>' \
            if calc_die.get('status') == 'OK' \
            else '<span class="badge badge-warn">要確認</span>'
        calc_sec = f"""
<table>
<tr><th>対象</th><th>応力 (MPa)</th><th>降伏応力 (MPa)</th><th>安全率</th><th>判定</th></tr>
<tr><td>パンチ 圧縮</td>
    <td>{calc_punch.get('sigma_comp_MPa', '-')}</td>
    <td>{calc_punch.get('yield_MPa', '-')}</td>
    <td>{calc_punch.get('sf_compression', '-')}</td>
    <td>{st_punch}</td></tr>
<tr><td>パンチ 座屈</td>
    <td>—</td>
    <td>—</td>
    <td>{calc_punch.get('sf_buckling', '-')}</td>
    <td>{st_punch}</td></tr>
<tr><td>ダイインサート フープ応力</td>
    <td>{calc_die.get('hoop_stress_MPa', '-')}</td>
    <td>{calc_die.get('yield_MPa', '-')}</td>
    <td>{calc_die.get('sf', '-')}</td>
    <td>{st_die}</td></tr>
</table>
"""
    else:
        calc_sec = '<p>CalculiX 解析を実行してください。</p>'

    # サマリー
    warnings = []
    if calc_punch and calc_punch.get('sf_compression', 99) < 2.0:
        warnings.append('⚠ パンチ圧縮安全率が 2.0 未満 — パンチ径を大きくするか SKH51 へ変更を推奨')
    if calc_punch and calc_punch.get('sf_buckling', 99) < 2.5:
        warnings.append('⚠ パンチ座屈安全率が 2.5 未満 — パンチ長さを短くするかガイドを追加してください')
    if calc_die and calc_die.get('sf', 99) < 2.0:
        warnings.append('⚠ ダイインサート安全率が 2.0 未満 — 肉厚を増やしてください')

    overall = '✅ 全項目 OK' if not warnings else f'⚠ {len(warnings)} 件の懸念事項'
    warn_html = ''.join(f'<p class="warn">{w}</p>' for w in warnings)

    summary_sec = f"""
<p style="font-size:1.2em;font-weight:bold;">{overall}</p>
{warn_html}
<div class="kv">
  <div class="kv-item"><div class="kv-label">総打ち抜き力</div>
    <div class="kv-value">{summary.get('total_force_kN', '-')} kN</div></div>
  <div class="kv-item"><div class="kv-label">必要プレス</div>
    <div class="kv-value">{summary.get('press_capacity_ton', '-')} ton</div></div>
  <div class="kv-item"><div class="kv-label">ストリップ幅</div>
    <div class="kv-value">{summary.get('strip_width_mm', '-')} mm</div></div>
  <div class="kv-item"><div class="kv-label">工程数</div>
    <div class="kv-value">{summary.get('station_count', '-')}</div></div>
</div>
"""

    html = TEMPLATE.format(
        timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        filename=params.get('filename', '-'),
        part_w=dims['width'],
        part_h=dims['height'],
        thickness=params.get('thickness', 1.0),
        mat_name=mat['name'],
        hole_count=len(geom.get('holes', [])),
        bend_count=len(geom.get('bends', [])),
        flat_w=blank['flat_width'],
        flat_h=blank['flat_height'],
        total_ba=blank['total_ba'],
        k_factor=mat['k_factor'],
        station_count=summary['station_count'],
        pitch=summary['pitch_mm'],
        strip_w=summary['strip_width_mm'],
        press_ton=summary['press_capacity_ton'],
        svg_content=layout.get('svg', ''),
        station_rows=rows,
        radioss_section=radioss_sec,
        calculix_section=calc_sec,
        summary_section=summary_sec,
    )
    return html
