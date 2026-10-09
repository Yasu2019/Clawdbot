# -*- coding: utf-8 -*-
"""Self-contained INC-188 summary report (videos/images embedded as data URIs)."""
import base64
import os

R = "D:/Temp/claude/C--Users-yasu-AppData-Roaming-Claude-scratch-workspaces-e1ebf325-cdfb-4f2b-b6a4-5defd1f2aa51-fa0c3823-f1b2-4dd9-9e5f-e3bb3a3cd731-scratch-2026-09-26-52c2f5/83ee61a5-e0e1-4979-b394-330c19f43a5d/scratchpad/report/"
A = "F:/clawstack_data/inc188/anim/"
T = "D:/Temp/rep2/"


def uri(path, mime):
    return f"data:{mime};base64," + base64.b64encode(open(path, "rb").read()).decode()


def vid(path):
    return f'<video src="{uri(path, "video/mp4")}" controls muted loop playsinline preload="metadata"></video>'


def img(path, alt):
    return f'<img src="{uri(path, "image/png")}" alt="{alt}">'


CSS = open(R + "INC188_report.html", encoding="utf-8").read()
CSS = CSS[CSS.index("<style>"):CSS.index("</style>") + 8]
CSS = CSS.replace("</style>", """
.tl td:first-child{white-space:nowrap;font-family:var(--mono);font-size:12.5px}
.lead2{font-size:15.5px}
.badge{font-family:var(--mono);font-size:11.5px;padding:1px 7px;border-radius:4px;border:1px solid var(--rule);color:var(--muted)}
</style>""")

tabs3d = [("t1", "実製品の順番・工具 250 µm（P1r21）", A + "anim2_P1r21.mp4",
           "P1r21：矩形 → トリム → 丸、GENE1 0.5。0.135〜0.600 ms。断面 A-A でスラグが押しつぶされ下面がふくらむのは、丸穴の切り口が割れきらないため（第 3 章）。"),
          ("t2", "実製品の順番・工具 30 µm（P1r28f）", A + "anim2_P1r28f.mp4",
           "P1r28f：工具の刃先を 30 µm にした版（標準時刻 0.504 ms まで）。H4 の最大ひずみは 0.66 から 0.46 に下がった。H2 が 0.324 ms で要素削除。"),
          ("t3", "丸 → 矩形 → トリム（P1r24f）", A + "anim2_P1r24f.mp4",
           "P1r24f：H4 の点の要素が 0.444 ms で消えるが、トリムのせん断帯の中の削除で、丸穴へ向かう実クラックとは別物。"),
          ("t4", "丸 → トリム → 矩形（P1r26f）", A + "anim2_P1r26f.mp4",
           "P1r26f：同上、H4 の点の要素が 0.474 ms で消える。0.234・0.264 ms のフレームは 10/5 の容量不足で欠落。")]

tab_btn = "".join(f'<button role="tab" id="b{k}" aria-selected="{"true" if i == 0 else "false"}" aria-controls="{k}">{lab}</button>'
                  for i, (k, lab, _, _) in enumerate(tabs3d))
tab_pan = "".join(f'<figure id="{k}" role="tabpanel"{"" if i == 0 else " hidden"}>{vid(p)}<figcaption>{cap}</figcaption></figure>'
                  for i, (k, _, p, cap) in enumerate(tabs3d))

html = f"""<title>INC-188 打ち抜き解析 総括</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans+JP:wght@400;500;700&display=swap">
{CSS}
<div class="wrap">
<header>
  <div class="eyebrow">INC-188 · PM7TCB 順送プレス 打ち抜き解析（OpenRadioss）</div>
  <h1>H4 のクラックはなぜ計算で出ないか — 総括と次の計算</h1>
  <div class="meta"><span>2026-10-09 時点</span><span>板 MR536-H34（AA5052 系）t0.5 mm</span><span>クリアランス 約 20 µm（4%）</span></div>
</header>

<section>
  <p class="lead">実製品の順番（矩形 → トリム → 丸）で H4 付近（トリムのフィレット）に入る微小クラックは、これまでの計算ではどの設定でも再現できていない。調べた結果、計算の割れの判定（材料が伸ばされてちぎれる「延性破壊」）では、実クラックの経路はほとんど傷まないことが分かった。一方で、丸穴を抜くあいだ、実クラックの経路には引張強さに近い引っ張りがかかる。現在は「トリムの切り口の微小な傷が、この引っ張りで開いた」という仮説を立て、パンチの引き抜きと、実金型に近い工程ごとの動きを加えた計算を進めている。</p>
  <div class="key">
    <div class="alert"><b>H4 が割れない理由（計算）</b><span>実クラックの経路の延性損傷は 0.14〜0.23（1 で破断）。トリム刃先の通過時に圧縮寄りのせん断でひずむだけで、割れの判定に届かない。</span></div>
    <div><b>実クラック経路の引っ張り</b><span>実製品の順番では、丸穴を抜くあいだ約 230 MPa（引張強さ 約 250 MPa）。丸を先に抜く順番では約 120 MPa まで下がる。</span></div>
    <div><b>除荷後の残留応力（実測）</b><span>KISTEC の X 線測定 8 点で −5.5〜+9.2 MPa とほぼ 0。高い引っ張りは打ち抜き中だけで、工具が抜けると抜ける。</span></div>
    <div><b>破断条件の問題</b><span>今の値はメッシュに合わせた値で、細かくするほど早く割れて収束しない。実物の切り口（せん断面 ≒ 破断面）で校正し直した。</span></div>
    <div><b>モデルと金型の違い</b><span>3 本のパンチが一緒に下がり、ストリッパーは全部の穴が開いたまま。丸穴を抜くあいだもトリムのパンチが H4 の切り口に刺さっている。工程ごとのモデルに作り直した。</span></div>
  </div>
</section>

<section>
  <h2><span class="no">1</span>これまでの経過</h2>
  <div class="tbl"><table class="tl">
    <thead><tr><th>時期</th><th>内容</th></tr></thead>
    <tbody>
      <tr><td>〜9/27</td><td>パンチが板を素通りしていた接触設定の不具合を発見・修正（<code>/SURF/PART/ALL</code>）。それ以前の H4 の結論は無効。</td></tr>
      <tr><td>9/28〜10/6</td><td>修正後のモデルで打ち抜き順番 5 通りを計算。H4 の点の要素が消えたのは丸を先に抜く 2 通りだけ（後に、実クラックとは別物と判明）。</td></tr>
      <tr><td>10/4〜10/5</td><td>文献調査（6 言語）。2D 軸対称で破断条件のメッシュ依存を確認。</td></tr>
      <tr><td>10/6</td><td>材料の値が引張試験と一致することを確認。製品の切り口資料（せん断面 ≒ 破断面）を校正の目標にした。工具刃先 30 µm の計算（P1r28f）。</td></tr>
      <tr><td>10/7</td><td>実クラックの経路に沿った応力・損傷の解析。KISTEC の残留応力の実測と比較。応力状態に応じた破断条件（BIQUAD）を校正。</td></tr>
      <tr><td>10/8</td><td>校正した値（GENE1 1.0）は 3D の粗い要素で計算が破綻すると判明。要素サイズに応じて破断ひずみを変える補正を実装・検証。パンチの引き抜きを加えた計算（P1r34f）開始。</td></tr>
      <tr><td>10/9</td><td>ご指摘を受け、工程ごとにパンチが 1 本ずつ動き、ストリッパーは抜く穴だけが開く「工程ごとのモデル」を作成（P1r36f・P1r37f）。</td></tr>
    </tbody>
  </table></div>
</section>

<section>
  <h2><span class="no">2</span>打ち抜きアニメーション（3D）</h2>
  <p>上段＝上から見た相当塑性ひずみと von Mises 応力（板厚方向の最大値）。下段＝断面 A-A（丸穴中心 → H4）と断面 B-B（矩形パンチの切断線を直角に横切る線）。断面線は上段の図に記号で示した。灰色はパンチ・ダイ・ストリッパーの断面。向きは Crack_発生位置_PM7TCB.pdf の拡大図と同じ。</p>
  <div class="tabs" role="tablist">{tab_btn}</div>
  {tab_pan}
</section>

<section>
  <h2><span class="no">3</span>H4 でクラックが出ない理由</h2>
  <h3>3-1 破断条件の値がメッシュの細かさで変わる（2D 軸対称の確認計算）</h3>
  <p>丸穴だけを軸対称で計算し、要素の大きさだけを変えた。どの破断条件も、メッシュを細かくするほど早く割れ、値が収束しない。今の値（GENE1 0.5、Cockcroft 19.1 MPa）は 3D のメッシュに合わせて決めた値で、物性値ではない。</p>
  <figure>{vid(T + "axi_mesh.mp4")}<figcaption>同じ破断条件（GENE1 0.5）で要素 20・5・2.5 µm。細かいほど早く切れる（分離時の押し込み量 138 → 90 → 70 µm）。</figcaption></figure>
  <h3>3-2 実物の切り口で破断条件を校正</h3>
  <p>クラックが出た製品そのものの資料では、切り口のせん断面と破断面がほぼ同じ高さ。これを目標にすると、要素 20 µm では GENE1 1.0、または BIQUAD（せん断 0.9〜1.0）が合う。Cockcroft は値を上げても届かない。</p>
  <figure>{vid(T + "axi_criteria.mp4")}<figcaption>左から、今の GENE1 0.5、今の Cockcroft 19.1 MPa、校正した GENE1 1.0、BIQUAD。今の 2 つは板厚の 1〜3 割で切れてしまい早すぎる。</figcaption></figure>
  <figure>{img(R + "axisym_calibration.png", "要素サイズと分離・校正図")}<figcaption>(a) 要素を細かくするほど分離が早まる。(b) 要素 20 µm での校正図（最大打抜き力とだれ）。緑の帯は打抜き力の理論値。</figcaption></figure>
  <h3>3-3 実クラックの経路では、割れるほど材料が伸ばされない</h3>
  <p>実クラックはトリムの輪郭から丸穴へ向かう。この経路から 60 µm 以内の全要素について、応力と延性損傷を時間を追って調べた。</p>
  <figure>{img(T + "crackpath.png", "実クラック経路の応力と損傷")}<figcaption>左：経路上の引張応力（工具が入ったまま）。右：延性損傷（1 で破断）。どの順番でも損傷は 0.14〜0.23 で頭打ち。実製品の順番（赤・橙）は丸穴を抜くあいだ 230 MPa 前後の引っ張りが続き、丸を先に抜く順番（緑）は 120 MPa 前後に下がる。</figcaption></figure>
  <div class="tbl"><table>
    <thead><tr><th>計算</th><th>打ち抜き順番・工具</th><th>経路上の最大損傷</th><th>丸穴を抜くあいだの引張応力</th></tr></thead>
    <tbody>
      <tr class="real"><td class="num">P1r21</td><td>矩形 → トリム → 丸（実製品）、工具 250 µm</td><td class="num">0.20</td><td class="num">約 230 MPa</td></tr>
      <tr class="real"><td class="num">P1r28f</td><td>同上、工具 30 µm</td><td class="num">0.14</td><td class="num">約 210 MPa</td></tr>
      <tr><td class="num">P1r24f</td><td>丸 → 矩形 → トリム</td><td class="num">0.21</td><td class="num">約 220 MPa</td></tr>
      <tr><td class="num">P1r26f</td><td>丸 → トリム → 矩形</td><td class="num">0.23</td><td class="num">約 120 MPa</td></tr>
    </tbody>
  </table></div>
  <h3>3-4 工具の形を正しくすると H4 のひずみは下がる</h3>
  <p>旧モデルでは工具の刃先が粗い多角形で、その角が H4 から 35 µm の位置にあった。刃先を 30 µm にすると（P1r28f）、H4 の最大ひずみは 0.66 から 0.46 に下がった。旧モデルの H4 の集中の約 3 割は見かけだった。</p>
  <h3>3-5 モデルと実金型の動きの違い</h3>
  <p>これまでのモデルは 3 本のパンチが一緒に下がり（高さの差で順番をつける）、1 枚のストリッパーに全部の穴が開いている。このため丸穴を抜くあいだも、矩形とトリムのパンチは切り口に刺さったままで、H4 のトリムの切り口にトリムパンチが横から触れている。実際の順送金型では、丸穴の工程にトリムのパンチはいない。</p>
  <figure>{vid(T + "schedule.mp4")}<figcaption>左：これまでのモデル（P1r34f）。右：工程ごとのモデル（P1r36f・P1r37f）。パンチは 1 本ずつ下りて抜いて上がり、まだ抜かない穴はストリッパーと一緒に動く栓（青）が押さえる。栓は自分のパンチが来る直前に板から離れる。横方向の寸法は模式。</figcaption></figure>
  <div class="note">
    <h3>現時点の解釈（仮説）</h3>
    <p>実クラックは、材料が大きく伸ばされてちぎれたもの（延性破壊）ではなく、トリムの切り口の微小な傷（破断面・バリ）を起点に、丸穴を抜くあいだにかかる引張強さに近い引っ張りで開いた微小き裂の可能性が高い。この引っ張りは工具が抜けると消えるため、測定された残留応力が小さいこととも矛盾しない。ひずみで判定する破断条件では、この形の割れは原理的に再現できない。</p>
  </div>
</section>

<section>
  <h2><span class="no">4</span>いま行っている計算と計画</h2>
  <div class="tbl"><table>
    <thead><tr><th>順</th><th>計算</th><th>内容</th><th>確かめること</th><th>完了見込み</th></tr></thead>
    <tbody>
      <tr><td>実行中</td><td class="num">P1r34f</td><td>これまでの動き ＋ パンチの引き抜きとストリッパーの解放（GENE1 0.5）</td><td>引き抜くときの切り口の引っ張り、除荷後の残留応力を KISTEC 8 点と比較</td><td class="num">10/9 14 時ごろ</td></tr>
      <tr><td>1</td><td class="num">P1r36f</td><td>工程ごとのモデル（GENE1 0.5）</td><td>トリムのパンチがいない状態で丸穴を抜いたとき、H4 の切り口の引っ張りがどう変わるか</td><td class="num">10/11 午後</td></tr>
      <tr><td>2</td><td class="num">P1r37f</td><td>工程ごとのモデル ＋ 校正した破断条件（GENE1 1.0、要素サイズ補正）</td><td>実物に近い割れ方での同じ確認</td><td class="num">10/13 ごろ</td></tr>
      <tr><td>3〜</td><td class="num">P1r28f 残り・P1r35f・P1r32f</td><td>比較用</td><td>—</td><td class="num">その後</td></tr>
    </tbody>
  </table></div>
  <div class="plan">
    <h3>計画</h3>
    <ol>
      <li>P1r34f と P1r36f を比べ、パンチとストリッパーの動きの違いが H4 の切り口の応力にどれだけ効くかを確かめる。</li>
      <li>除荷後の残留応力を KISTEC の 8 点と比べ、モデルの妥当性を確かめる（写真の向きとモデルの軸の対応は未確定のため、全向きを調べて候補を出す）。</li>
      <li>引っ張りでき裂が開くかどうかの判定（切り口の傷を想定した応力集中・破壊力学的な見方）を検討する。</li>
      <li>ストリッパーを押さえ力で制御する（打抜き力の 10〜20%、切り口 1 mm あたり約 6〜16 N）。</li>
    </ol>
  </div>
  <div class="plan">
    <h3>実物でご確認いただきたいこと</h3>
    <ol>
      <li>クラックの起点が、トリムの切り口の破断面側かバリ側か（仮説の検証にいちばん効く）。</li>
      <li>丸穴を中心で切断した断面の、だれ・せん断面・破断面の高さ（破断条件の値を確定できる）。</li>
      <li>H1・H2 の ×230 程度での観察。</li>
      <li>実金型のクリアランス（モデルは約 20 µm、トリムの曲がり部で局所 11 µm）。</li>
    </ol>
  </div>
</section>

<section>
  <h2><span class="no">5</span>計算の運用で起きたことと対策</h2>
  <div class="tbl"><table>
    <thead><tr><th>日</th><th>起きたこと</th><th>対策（いずれも試験済み）</th></tr></thead>
    <tbody>
      <tr><td>10/4</td><td>再開用ファイルの書き込み中に停止し、7.5 時間止まった</td><td>書き終わりを確認してから停止。壊れていれば 1 つ前から再開</td></tr>
      <tr><td>10/5</td><td>作業ドライブ（E:）が満杯になり停止</td><td>実ドライブの空きを監視し、完了した計算のファイルを自動で G: へ移動</td></tr>
      <tr><td>10/7</td><td>前進しながら異常終了を繰り返す計算を打ち切っていた。破綻したのに「正常終了」と表示され完了扱いになった</td><td>前進が無いときだけ打ち切り。目標時刻前の正常終了は異常扱い</td></tr>
      <tr><td>10/8</td><td>節点が飛び、質量の自動追加が破綻を吸収して計算が続いた</td><td>追加質量が全体の 5% を超えたら停止</td></tr>
    </tbody>
  </table></div>
</section>

<footer>解析：OpenRadioss（K10、12 スレッド）。数値はすべて実計算の結果から抽出。動画は計算のフレームから作成（パンチとストリッパーの動きの動画のみ模式図）。</footer>
</div>
<script>
(function(){{
  var ids={[k for k, *_ in tabs3d]!r};
  ids.forEach(function(k){{
    document.getElementById("b"+k).addEventListener("click",function(){{
      ids.forEach(function(j){{
        var on=j===k; document.getElementById("b"+j).setAttribute("aria-selected",on?"true":"false");
        var p=document.getElementById(j); p.hidden=!on; var v=p.querySelector("video"); if(!on&&v){{v.pause();}}
      }});
    }});
  }});
}})();
</script>
"""
open(T + "INC188_総括_20261009.html", "w", encoding="utf-8").write(html)
print(len(html) // 1024, "KB")
