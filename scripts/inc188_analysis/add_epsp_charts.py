# -*- coding: utf-8 -*-
"""rupture_sensitivity_report.html に「ひずみ蓄積の時系列(εp)」セクション(01b)を追加する。
データは timeseries_*.json から読む。チャートは素のSVG+JS(ホバーのクロスヘア/ツールチップ、
数値表ビュー付き)。色はdataviz検証済みのカテゴリカル6色(ライト/ダークで別ステップ)。
"""
import json

import os
BASE = os.environ.get("INC188_WORK", os.getcwd())   # timeseries_*.json と report html があるディレクトリ
REPORT = f"{BASE}\\rupture_sensitivity_report.html"


def load(fn):
    return json.load(open(f"{BASE}\\{fn}", encoding="utf-8"))


base = load("timeseries_6hotspots.json")          # P1r7
runs = {
    "P1r7": base,
    "P1r8": load("timeseries_P1r8.json"),
    "P1r9": load("timeseries_P1r9.json"),
    "P1r10": load("timeseries_P1r10.json"),
    "P1r11": load("timeseries_P1r11.json"),
    "P1r12": load("timeseries_P1r12.json"),
}


def series_from(ts, sid, label, color):
    """破断した要素は破断フレームまで(その点を含む)を描き、以降はnull。"""
    ys, rupt = [], None
    for i, p in enumerate(ts):
        if rupt is not None:
            ys.append(None)
        elif p["status"] == "ruptured":
            rupt = i
            ys.append(round(p["eps"], 4))
        else:
            ys.append(round(p["eps"], 4))
    return {"id": sid, "label": label, "color": color, "y": ys, "rupt": rupt}


times = [round(p["t"] * 1e3, 4) for p in base["H4"]]

# --- chart 1: P1r7基準条件、ホットスポット別 ---
order1 = [("H4", "H4(実クラック位置)"), ("H1", "H1"), ("H2", "H2"),
          ("H5", "H5"), ("H3", "H3"), ("H2b", "H2b")]
chart1 = {
    "times": times, "xMax": 0.6, "yMax": 0.7, "yTicks": [0, 0.2, 0.4, 0.6],
    "series": [series_from(base[k], k, lab, i + 1) for i, (k, lab) in enumerate(order1)],
    "annot": ["H4"],                  # 破断点に直接注記
    "rlabels": [{"keys": ["H1"], "text": "H1"}, {"keys": ["H2"], "text": "H2"},
                {"keys": ["H5"], "text": "H5"}],
    "ticks": [{"t": 0.17, "text": "矩形接触"}, {"t": 0.29, "text": "トリム接触"},
              {"t": 0.41, "text": "丸接触"}],
    "aria": "P1r7基準条件における6ホットスポットの等価塑性ひずみの時間変化。H4のみ0.315msで破断。",
}

# --- chart 2: H4を6条件で比較 ---
order2 = [("P1r7", "P1r7 基準"), ("P1r8", "P1r8 +COCKCROFT"), ("P1r9", "P1r9 クリアランス10µm"),
          ("P1r10", "P1r10 クリアランス30µm"), ("P1r11", "P1r11 順番入替"), ("P1r12", "P1r12 メッシュ50µm")]
chart2 = {
    "times": times, "xMax": 0.6, "yMax": 0.7, "yTicks": [0, 0.2, 0.4, 0.6],
    "series": [series_from(runs[k]["H4"], k, lab, i + 1) for i, (k, lab) in enumerate(order2)],
    "annot": ["P1r7"], "mr": 150,
    "rlabels": [{"keys": ["P1r8"], "text": "P1r8"}, {"keys": ["P1r11"], "text": "P1r11"},
                {"keys": ["P1r9", "P1r10"], "text": "P1r9・P1r10"}, {"keys": ["P1r12"], "text": "P1r12"}],
    "ticks": [],
    "aria": "H4の等価塑性ひずみの時間変化を6条件で比較。基準条件のみ0.315msで破断。",
}

CSS = """
  :root{
    --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --s4:#eda100; --s5:#e87ba4; --s6:#008300;
  }
  @media (prefers-color-scheme: dark){
    :root:not([data-theme="light"]){
      --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500; --s5:#d55181; --s6:#008300;
    }
  }
  :root[data-theme="dark"]{
    --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500; --s5:#d55181; --s6:#008300;
  }
  .viz h3{font-size:15px;font-weight:700;margin:0 0 4px;}
  .viz .viz-sub{font-size:12.5px;color:var(--ink-soft);margin:0 0 10px;}
  .viz-legend{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:12.5px;margin-bottom:10px;}
  .viz-legend .k{display:inline-flex;align-items:center;gap:7px;color:var(--ink);}
  .viz-legend .k i{display:inline-block;width:18px;height:0;border-top:2px solid var(--c);}
  .viz-plot{position:relative;overflow-x:auto;}
  .viz-plot svg{display:block;min-width:620px;width:100%;height:auto;touch-action:pan-y;}
  .viz-plot svg:focus-visible{outline:2px solid var(--accent);outline-offset:2px;}
  .viz-tip{position:absolute;pointer-events:none;background:var(--panel);border:1px solid var(--line);
    border-radius:6px;padding:8px 10px;font-size:12px;min-width:168px;box-shadow:0 2px 10px rgba(0,0,0,.14);z-index:2;}
  .viz-tip[hidden]{display:none;}
  .viz-tip .th{font-family:"JetBrains Mono",monospace;color:var(--ink-soft);margin-bottom:5px;}
  .viz-tip .row{display:flex;align-items:center;gap:7px;line-height:1.55;}
  .viz-tip .row i{display:inline-block;width:12px;height:0;border-top:2px solid var(--c);flex:none;}
  .viz-tip .row b{font-family:"JetBrains Mono",monospace;font-weight:600;color:var(--ink);min-width:44px;text-align:right;}
  .viz-tip .row span{color:var(--ink-soft);}
  .viz-table{margin-top:10px;font-size:12.5px;}
  .viz-table summary{cursor:pointer;color:var(--ink-soft);}
  .viz-tablewrap{max-height:260px;overflow:auto;margin-top:8px;border:1px solid var(--line-soft);border-radius:4px;}
  .viz-tablewrap table{font-size:12px;}
  .viz-tablewrap th,.viz-tablewrap td{padding:4px 8px;font-variant-numeric:tabular-nums;white-space:nowrap;}
  .viz-tablewrap td{font-family:"JetBrains Mono",monospace;text-align:right;}
  .viz-tablewrap thead th{position:sticky;top:0;background:var(--panel);}
"""

JS = r"""
(function(){
  var NS='http://www.w3.org/2000/svg';
  function el(n,a,p){var e=document.createElementNS(NS,n);for(var k in a)e.setAttribute(k,a[k]);if(p)p.appendChild(e);return e;}
  function build(root){
    var cfg=JSON.parse(root.querySelector('script[type="application/json"]').textContent);
    var mr=cfg.mr||104,W=50+566+mr,H=340,M={l:50,r:mr,t:cfg.ticks.length?40:16,b:36};
    var pw=W-M.l-M.r,ph=H-M.t-M.b;
    var X=function(t){return M.l+t/cfg.xMax*pw;},Y=function(v){return M.t+ph*(1-v/cfg.yMax);};
    var plot=root.querySelector('.viz-plot'),tip=root.querySelector('.viz-tip');
    var svg=el('svg',{viewBox:'0 0 '+W+' '+H,role:'img','aria-label':cfg.aria,tabindex:'0'});
    plot.insertBefore(svg,tip);
    var css=function(v){return 'var('+v+')';};
    var fT='"Noto Sans JP",sans-serif',fM='"JetBrains Mono",monospace';
    // grid + y ticks
    cfg.yTicks.forEach(function(v){
      el('line',{x1:M.l,x2:W-M.r,y1:Y(v),y2:Y(v),stroke:css('--line-soft'),'stroke-width':1},svg);
      var t=el('text',{x:M.l-8,y:Y(v)+4,'text-anchor':'end','font-size':11,'font-family':fM,fill:css('--ink-soft')},svg);
      t.textContent=v.toFixed(1);
    });
    var yl=el('text',{x:M.l-8,y:M.t-6,'text-anchor':'end','font-size':11,'font-family':fT,fill:css('--ink-soft')},svg);
    yl.textContent='εp';
    // x ticks
    for(var xv=0;xv<=cfg.xMax+1e-9;xv+=0.1){
      el('line',{x1:X(xv),x2:X(xv),y1:M.t+ph,y2:M.t+ph+4,stroke:css('--line'),'stroke-width':1},svg);
      var tx=el('text',{x:X(xv),y:M.t+ph+17,'text-anchor':'middle','font-size':11,'font-family':fM,fill:css('--ink-soft')},svg);
      tx.textContent=xv.toFixed(1);
    }
    el('line',{x1:M.l,x2:W-M.r,y1:M.t+ph,y2:M.t+ph,stroke:css('--line'),'stroke-width':1},svg);
    var xu=el('text',{x:W-M.r,y:M.t+ph+31,'text-anchor':'end','font-size':11,'font-family':fT,fill:css('--ink-soft')},svg);
    xu.textContent='時間 t [ms]';
    // punch-contact hairlines
    cfg.ticks.forEach(function(k){
      el('line',{x1:X(k.t),x2:X(k.t),y1:M.t-4,y2:M.t+ph,stroke:css('--line'),'stroke-width':1},svg);
      var tt=el('text',{x:X(k.t)+4,y:M.t-8,'font-size':11,'font-family':fT,fill:css('--ink-soft')},svg);
      tt.textContent=k.text+' ≈'+k.t.toFixed(2);
    });
    // lines
    var byId={};
    cfg.series.forEach(function(s){
      byId[s.id]=s;
      var d='',pen=false;
      s.y.forEach(function(v,i){
        if(v===null){pen=false;return;}
        d+=(pen?'L':'M')+X(cfg.times[i]).toFixed(1)+' '+Y(v).toFixed(1);pen=true;
      });
      el('path',{d:d,fill:'none',stroke:css('--s'+s.color),'stroke-width':2,'stroke-linejoin':'round','stroke-linecap':'round'},svg);
    });
    // end markers (surface ring + dot)
    function endIdx(s){var j=-1;s.y.forEach(function(v,i){if(v!==null)j=i;});return j;}
    cfg.series.forEach(function(s){
      var j=endIdx(s);if(j<0)return;
      el('circle',{cx:X(cfg.times[j]),cy:Y(s.y[j]),r:6,fill:css('--panel')},svg);
      el('circle',{cx:X(cfg.times[j]),cy:Y(s.y[j]),r:4,fill:css('--s'+s.color)},svg);
    });
    // rupture annotations (next to the dot)
    (cfg.annot||[]).forEach(function(id){
      var s=byId[id],j=s.rupt;if(j===null)return;
      var x=X(cfg.times[j]),y=Y(s.y[j]);
      var a=el('text',{x:x+11,y:y-2,'font-size':12,'font-family':fT,'font-weight':700,fill:css('--ink')},svg);
      a.textContent=s.label.split(' ')[0]+' 破断 t='+cfg.times[j].toFixed(3)+'ms';
      var b=el('text',{x:x+11,y:y+13,'font-size':11,'font-family':fM,fill:css('--ink-soft')},svg);
      b.textContent='εp='+s.y[j].toFixed(3);
    });
    // right-margin labels with leader lines (min 15px apart)
    var items=(cfg.rlabels||[]).map(function(r){
      var ss=r.keys.map(function(k){return byId[k];});
      var yv=ss.map(function(s){return s.y[endIdx(s)];});
      var v=yv.reduce(function(a,b){return a+b;},0)/yv.length;
      return {r:r,s:ss[0],ss:ss,y:Y(v),ly:Y(v),v:v};
    }).sort(function(a,b){return a.y-b.y;});
    for(var i=1;i<items.length;i++){if(items[i].ly-items[i-1].ly<15)items[i].ly=items[i-1].ly+15;}
    items.forEach(function(it){
      var j=endIdx(it.s),ex=X(cfg.times[j]),lx=W-M.r+14;
      el('polyline',{points:(ex+7)+','+it.y+' '+(lx-5)+','+it.ly,fill:'none',stroke:css('--line'),'stroke-width':1},svg);
      var n=it.ss.length,w=(12-2*(n-1))/n;
      it.ss.forEach(function(sx,q){el('line',{x1:lx+q*(w+2),x2:lx+q*(w+2)+w,y1:it.ly,y2:it.ly,stroke:css('--s'+sx.color),'stroke-width':2,'stroke-linecap':'round'},svg);});
      var t=el('text',{x:lx+17,y:it.ly+4,'font-size':11.5,'font-family':fT,fill:css('--ink')},svg);
      t.textContent=it.r.text+' '+it.v.toFixed(2);
    });
    // hover layer
    var cross=el('line',{y1:M.t,y2:M.t+ph,stroke:css('--ink-soft'),'stroke-width':1,visibility:'hidden'},svg);
    var hit=el('rect',{x:M.l,y:M.t,width:pw,height:ph,fill:'transparent'},svg);
    var cur=-1;
    function show(i){
      i=Math.max(0,Math.min(cfg.times.length-1,i));cur=i;
      var x=X(cfg.times[i]);
      cross.setAttribute('x1',x);cross.setAttribute('x2',x);cross.setAttribute('visibility','visible');
      tip.hidden=false;tip.textContent='';
      var th=document.createElement('div');th.className='th';th.textContent='t = '+cfg.times[i].toFixed(3)+' ms';tip.appendChild(th);
      cfg.series.forEach(function(s){
        var row=document.createElement('div');row.className='row';
        var k=document.createElement('i');k.style.setProperty('--c','var(--s'+s.color+')');
        var b=document.createElement('b');
        var v=s.y[i];
        b.textContent=(v===null)?'破断済':v.toFixed(3);
        var n=document.createElement('span');n.textContent=s.label;
        row.appendChild(k);row.appendChild(b);row.appendChild(n);tip.appendChild(row);
      });
      var box=svg.getBoundingClientRect(),sc=box.width/W;
      var left=x*sc+14;
      if(left+tip.offsetWidth>plot.clientWidth+plot.scrollLeft-4)left=x*sc-tip.offsetWidth-14;
      tip.style.left=Math.max(4,left)+'px';tip.style.top=(M.t*sc+4)+'px';
    }
    function hide(){cross.setAttribute('visibility','hidden');tip.hidden=true;cur=-1;}
    hit.addEventListener('pointermove',function(e){
      var box=svg.getBoundingClientRect(),sc=box.width/W;
      var t=((e.clientX-box.left)/sc-M.l)/pw*cfg.xMax;
      show(Math.round(t/(cfg.times[1]-cfg.times[0])));
    });
    hit.addEventListener('pointerleave',hide);
    svg.addEventListener('keydown',function(e){
      if(e.key==='ArrowRight'){show((cur<0?0:cur)+1);e.preventDefault();}
      else if(e.key==='ArrowLeft'){show((cur<0?0:cur)-1);e.preventDefault();}
      else if(e.key==='Escape'){hide();}
    });
    svg.addEventListener('blur',hide);
    // legend
    var lg=root.querySelector('.viz-legend');
    cfg.series.forEach(function(s){
      var k=document.createElement('span');k.className='k';
      var i=document.createElement('i');i.style.setProperty('--c','var(--s'+s.color+')');
      k.appendChild(i);k.appendChild(document.createTextNode(s.label));lg.appendChild(k);
    });
    // table view
    var tw=root.querySelector('.viz-tablewrap'),tb=document.createElement('table');
    var hd='<thead><tr><th>t [ms]</th>';
    var thead=document.createElement('thead'),trh=document.createElement('tr');
    var th0=document.createElement('th');th0.textContent='t [ms]';trh.appendChild(th0);
    cfg.series.forEach(function(s){var th=document.createElement('th');th.textContent=s.label;trh.appendChild(th);});
    thead.appendChild(trh);tb.appendChild(thead);
    var tbody=document.createElement('tbody');
    cfg.times.forEach(function(t,i){
      var tr=document.createElement('tr');
      var c0=document.createElement('td');c0.textContent=t.toFixed(3);tr.appendChild(c0);
      cfg.series.forEach(function(s){
        var td=document.createElement('td'),v=s.y[i];
        td.textContent=(v===null)?'―':(v.toFixed(3)+(s.rupt===i?' 破断':''));
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    tb.appendChild(tbody);tw.appendChild(tb);
  }
  document.querySelectorAll('.viz[data-chart]').forEach(build);
})();
"""


def block(cfg, title, sub):
    return (
        '    <div class="viz card" data-chart>\n'
        f'      <h3>{title}</h3>\n'
        f'      <p class="viz-sub">{sub}</p>\n'
        '      <div class="viz-legend"></div>\n'
        '      <div class="viz-plot"><div class="viz-tip" hidden></div></div>\n'
        '      <details class="viz-table"><summary>数値表を表示(41フレーム)</summary>'
        '<div class="viz-tablewrap"></div></details>\n'
        f'      <script type="application/json">{json.dumps(cfg, ensure_ascii=False, separators=(",", ":"))}</script>\n'
        '    </div>\n'
    )


SECTION = (
    '\n  <section>\n'
    '    <div class="sec-label"><span class="num">01b</span><h2>ひずみ蓄積の時系列(等価塑性ひずみ &epsilon;p)</h2></div>\n'
    '    <p>各ホットスポットの最近接要素の&epsilon;pを、41フレーム(15&micro;s刻み)で追った。&epsilon;pはGENE1が内部で判定に使うせん断ひずみとは別の量なので、'
    '「破断にどれだけ近いか」ではなく<b>いつ・どのパンチの作用で変形が進んだか</b>を見るために使う(06章の注記)。'
    '破断判定はあくまで01章のマトリクス(EROSION_STATUS)。</p>\n'
    + block(chart1, "P1r7基準条件:ホットスポット別の&epsilon;p",
            "縦線は各パンチが材料に接触する時刻の目安(0.6mmの段差÷5m/s≒0.12ms刻み)。矩形0.17ms、トリム0.29ms、丸0.41ms。")
    + '    <p class="note" style="margin-top:12px;">'
    'H1は矩形の接触(約0.17ms)と同時に立ち上がり、0.444で頭打ちになる。H4・H2・H5・H3はトリムの接触(約0.29ms)以降に立ち上がる。'
    'H4は0.285msから立ち上がり、<b style="color:var(--ink);">0.315msに破断(&epsilon;p=0.585)</b>。H2bは最後までほぼ0(最大0.009)で、荷重をほとんど受けていない。'
    '各線は破断フレームで止め、破断後は描いていない。'
    '</p>\n'
    + '    <div style="height:20px"></div>\n'
    + block(chart2, "H4の&epsilon;p:6条件の比較",
            "同じ要素(H4)を、基準条件と5つの変更条件で追った。抜き順番を変えたP1r11は接触順が違うため縦線は付けていない。")
    + '    <p class="note" style="margin-top:12px;">'
    '破断するのは基準(P1r7)だけで、他の5条件は破断に至らない。COCKCROFT併用(P1r8)は0.30ms以降、&epsilon;pが0.2702のまま完全に一定。'
    'クリアランス10&micro;m・30&micro;m(P1r9・P1r10)は全フレームで差が最大0.0012とほぼ重なり、0.47まで進んで止まる。'
    'メッシュ50&micro;m(P1r12)は0.499まで達したが破断しない。抜き順番を入れ替えたP1r11は立ち上がりが0.165msに前倒しされており、'
    'トリムが先に接触するようになった(入替が意図どおり効いた)ことの裏付けにもなる。'
    '</p>\n'
    '  </section>\n'
)


def main():
    html = open(REPORT, encoding="utf-8").read()
    if "data-chart" in html:
        raise SystemExit("already inserted - refusing to duplicate")
    html = html.replace("</style>", CSS + "</style>", 1)
    marker = '  <section>\n    <div class="sec-label"><span class="num">02</span>'
    idx = html.index(marker)
    html = html[:idx] + SECTION.lstrip("\n") + "\n" + html[idx:]
    # JS is appended once before the closing wrap div's end (after footer)
    end = html.rindex("</div>")
    html = html[:end] + "<script>" + JS + "</script>\n" + html[end:]
    open(REPORT, "w", encoding="utf-8").write(html)

    # standalone preview (head/CSS + only the new section) for one local render check
    head_end = html.index('<div class="wrap">')
    prev = html[:head_end] + '<div class="wrap">' + SECTION + "<script>" + JS + "</script></div>"
    open(f"{BASE}\\epsp_preview.html", "w", encoding="utf-8").write(prev)
    print("ok; report bytes:", len(html.encode("utf-8")))


if __name__ == "__main__":
    main()
