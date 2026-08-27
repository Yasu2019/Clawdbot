const $=s=>document.querySelector(s);const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[c]));
async function api(url,opt={}){const r=await fetch(url,opt);if(!r.ok)throw new Error(await r.text());return r.json()}
document.querySelectorAll('nav button').forEach(b=>b.onclick=()=>{document.querySelectorAll('nav button,.tab').forEach(x=>x.classList.remove('active'));b.classList.add('active');$('#tab-'+b.dataset.tab).classList.add('active');if(b.dataset.tab==='samples')loadSamples();if(b.dataset.tab==='tags')loadTags();if(b.dataset.tab==='cases')loadCases();if(b.dataset.tab==='reviews')loadReviews();if(b.dataset.tab==='models')loadModels();if(b.dataset.tab==='metrics')loadMetrics()});
Promise.all([
  api('/api/health'),
  api('/api/metrics').catch(()=>({}))
]).then(([h,m])=>{
  $('#health').textContent=`稼働中 / 外部API無効=${h.external_api_disabled} / Champion=${h.champion_count ?? '-'}`;
  const nDec=(m.decisions||[]).reduce((s,r)=>s+(Number(r.count)||0),0);
  const nRev=(m.reviews||[]).reduce((s,r)=>s+(Number(r.count)||0),0);
  const bar=$('#factBar');
  if(bar){
    bar.innerHTML='<strong>FACT</strong> 検査='+nDec+' reviews='+nRev
      +' Champion='+(h.champion_count ?? '-')
      +' ／ P027 visual_inspection 2026-08-27 n=1 awaiting_human (machine_verified=0)'
      +' ／ 量産MSA・商用AOI同等とは書かない。3D深さは未校正のまま高精度としない。Challengerは自動昇格しない。';
  }
}).catch(()=>{
  $('#health').textContent='接続エラー';
  const bar=$('#factBar');
  if(bar) bar.textContent='API に接続できません。projects\\visual_inspection_ai\\windows\\start_api.ps1 (port 18010)';
});
const ITEM_JP={width_mm:'部品外形幅 [mm]',height_mm:'部品外形高さ [mm]',hole_diameter_mm:'穴径 [mm]',scratch_width_mm:'傷 幅 [mm]',scratch_depth_mm:'傷 深さ [mm]',dent_width_mm:'打痕 幅 [mm]',dent_depth_mm:'打痕 深さ [mm]'};
const renderMeasurementsTable=items=>{if(!Array.isArray(items)||!items.length)return'';const rows=items.map(m=>{const label=ITEM_JP[m.name]||m.name;const val=(m.value_mm!==null&&m.value_mm!==undefined)?m.value_mm.toFixed(4):'-';const spec=(m.lower_mm!==null?m.lower_mm:'')+' ～ '+(m.upper_mm!==null?m.upper_mm:'');let badge='<span class="badge-none">未判定</span>';if(m.passed===true)badge='<span class="badge-ok">適合 (OK)</span>';else if(m.passed===false)badge='<span class="badge-ng">規格外 (NG)</span>';return `<tr><td><b>${esc(label)}</b></td><td>${val}</td><td>${esc(spec)}</td><td>${badge}</td></tr>`}).join('');return `<h3>寸法・欠陥計測結果 (幅・深さ評価)</h3><table class="measurement-table"><thead><tr><th>計測項目</th><th>測定値 [mm]</th><th>公差規格 [mm]</th><th>判定</th></tr></thead><tbody>${rows}</tbody></table>`};

$('#inspect-form').onsubmit=async e=>{e.preventDefault();$('#inspect-message').textContent='検査中...';const fd=new FormData(e.target);try{const x=await api('/api/inspect',{method:'POST',body:fd});$('#inspect-message').textContent='完了';$('#result').innerHTML=`<div><div class="decision ${x.decision}">${x.decision}</div><p>異常スコア: ${x.anomaly_score.toFixed(5)}</p><p>${x.reasons.map(esc).join('<br>')}</p><p>モデル: ${esc(x.model_version)}</p>${renderMeasurementsTable(x.measurements)}<details><summary>詳細ログ / 処理時間 (ms)</summary><pre>${esc(JSON.stringify(x.elapsed_ms,null,2))}</pre></details></div><div><figure><figcaption>判定結果(NG箇所=赤枠)</figcaption><img src="${x.annotated_image_url}?t=${Date.now()}"></figure>${x.heatmap_image_url?`<figure><figcaption>異常ヒートマップ(青=正常/赤=異常)</figcaption><img src="${x.heatmap_image_url}?t=${Date.now()}"></figure>`:``}</div>`}catch(err){$('#inspect-message').textContent='失敗: '+err.message}};

async function loadReviews(){const status=$('#review-status').value;const rows=await api('/api/reviews?status='+encodeURIComponent(status));$('#reviews').innerHTML=rows.length?rows.map(r=>`<div class="review-card"><h3>${esc(r.product_id)} / AI=${esc(r.ai_decision)} / score=${Number(r.anomaly_score).toFixed(4)}</h3><p>${esc(r.ai_reason)}</p><div class="review-images"><img src="${r.original_url}"><img src="${r.annotated_url}"></div>${r.status==='PENDING'?`<div class="review-actions"><select id="d-${r.id}"><option>OK</option><option>NG</option></select><input id="m-${r.id}" placeholder="不良モード"><input id="c-${r.id}" placeholder="コメント"><button onclick="labelReview('${r.id}')">確定</button></div>`:`<p>確定=${esc(r.user_decision)} / ${esc(r.defect_mode)} / ${esc(r.comment)}</p>`}</div>`).join(''):'対象なし'}
window.labelReview=async id=>{await api(`/api/reviews/${id}/label`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({decision:$('#d-'+id).value,defect_mode:$('#m-'+id).value,comment:$('#c-'+id).value,use_for_training:true,reviewer:'local_user'})});loadReviews()};
async function loadModels(){const rows=await api('/api/models');$('#models').innerHTML=rows.map(m=>`<div class="model-card"><b>${esc(m.version)}</b> / ${esc(m.product_id)} / <b>${esc(m.stage)}</b><br>kind=${esc(m.kind)}<br>created=${esc(m.created_at)} ${m.stage!=='CHAMPION'?`<button onclick="promoteModel('${m.version}')">手動昇格</button>`:''}</div>`).join('')||'モデルなし'}
window.promoteModel=async v=>{if(!confirm(`${v} をChampionへ昇格しますか？`))return;await api(`/api/models/${v}/promote`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({confirm:true,approved_by:'local_user',note:'UI manual approval'})});loadModels()};
async function loadMetrics(){$('#metrics').textContent=JSON.stringify(await api('/api/metrics'),null,2)}
const GROUP_JP={measure:'寸法測定デモ',press:'プレス部品デモ',resin:'樹脂成形品デモ',real_solder_joint:'はんだ付け外観(Solder Joint)',real_solder_joint_patchcore:'はんだ付け外観(PatchCore)',real_work_pcb1:'電子基板PCB(VisA)',real_work_pipe_fryum:'樹脂成形パイプ(VisA)',real_work_metal_nut:'金属ナット(MVTec)',real_work_screw:'ネジ外観(MVTec)',real_work_capsule:'樹脂カプセル(MVTec)'};
const groupName=g=>GROUP_JP[g]||(g&&g.startsWith('real_work_')?'実データセット/'+g.slice(10):g);
async function loadSamples(){const rows=await api('/api/samples');const sel=$('#sample-group');const groups=[...new Set(rows.map(r=>r.group))];const cur=sel.value;sel.innerHTML='<option value="">全グループ</option>'+groups.map(g=>`<option value="${esc(g)}" ${g===cur?'selected':''}>${esc(groupName(g))}</option>`).join('');const shown=sel.value?rows.filter(r=>r.group===sel.value):rows;$('#samples').innerHTML=shown.length?shown.map(r=>`<div class="review-card"><h3><span class="decision ${esc(r.verdict)}" style="font-size:1.1rem">${esc(r.verdict)}</span> ${esc(r.title)}</h3><p>${esc(r.caption).replace(/\n/g,'<br>')}</p><div class="review-images"><figure><figcaption>判定結果</figcaption><img src="${r.annotated_url}?t=${Date.now()}"></figure>${r.heatmap_url?`<figure><figcaption>異常ヒートマップ(青=正常/赤=異常)</figcaption><img src="${r.heatmap_url}?t=${Date.now()}"></figure>`:'<p>(ヒートマップなし)</p>'}</div></div>`).join(''):'サンプルなし — scripts/measure_demo.py 等のデモ実行で登録されます'}
$('#reload-samples').onclick=loadSamples;$('#sample-group').onchange=loadSamples;

// ---- サンプルタグ / 外観毎の判定事例 (2026-07-15追加) ----
// 外観カテゴリ: name="<カテゴリ>_<ファイル名>" 形式から末尾要素を除いて推定。tags配列があれば優先。
const caseCategory=r=>{if(Array.isArray(r.tags)&&r.tags.length)return r.tags[0];const parts=String(r.name||'').split('_');return parts.length>1?parts.slice(0,-1).join('_'):(r.name||'不明')};
const CAT_JP={good:'良品',normal:'良品(半田正常)',excessive:'半田過多',insufficient:'半田不足',shifted_component:'部品位置ズレ',short:'ブリッジ(短絡)',bent:'曲がり',scratch:'キズ',color:'変色',flip:'反転',crack:'割れ',hole:'穴',cut:'切断',thread:'糸残り',metal_contamination:'金属異物'};
const catName=c=>CAT_JP[c]?`${CAT_JP[c]} (${c})`:c;
const sampleTags=r=>{const t=new Set();t.add(groupName(r.group));t.add(catName(caseCategory(r)));t.add(r.verdict);(r.tags||[]).forEach(x=>t.add(x));return[...t]};
const sampleCard=r=>`<div class="review-card"><h3><span class="decision ${esc(r.verdict)}" style="font-size:1.1rem">${esc(r.verdict)}</span> ${esc(r.title)}</h3><p class="tagline">${sampleTags(r).map(t=>`<span class="tag-chip small">${esc(t)}</span>`).join('')}</p><p>${esc(r.caption).replace(/\n/g,'<br>')}</p><div class="review-images"><figure><figcaption>判定結果</figcaption><img loading="lazy" src="${r.annotated_url}?t=${Date.now()}"></figure>${r.heatmap_url?`<figure><figcaption>異常ヒートマップ(青=正常/赤=異常)</figcaption><img loading="lazy" src="${r.heatmap_url}?t=${Date.now()}"></figure>`:'<p>(ヒートマップなし)</p>'}</div></div>`;
let activeTags=new Set();
async function loadTags(){const rows=await api('/api/samples');const counts=new Map();rows.forEach(r=>sampleTags(r).forEach(t=>counts.set(t,(counts.get(t)||0)+1)));[...activeTags].forEach(t=>{if(!counts.has(t))activeTags.delete(t)});
$('#tag-cloud').innerHTML=[...counts.entries()].sort((a,b)=>b[1]-a[1]).map(([t,n])=>`<button class="tag-chip ${activeTags.has(t)?'on':''}" data-tag="${esc(t)}">${esc(t)} <b>${n}</b></button>`).join('')||'サンプル未登録 — デモ実行で登録されます';
document.querySelectorAll('#tag-cloud .tag-chip').forEach(b=>b.onclick=()=>{const t=b.dataset.tag;activeTags.has(t)?activeTags.delete(t):activeTags.add(t);loadTags()});
const shown=activeTags.size?rows.filter(r=>{const ts=sampleTags(r);return[...activeTags].every(t=>ts.includes(t))}):rows;
$('#tag-results').innerHTML=`<p class="muted">${shown.length}/${rows.length}件表示${activeTags.size?` (絞り込み: ${esc([...activeTags].join(' + '))})`:''}</p>`+shown.map(sampleCard).join('')}
$('#reload-tags').onclick=loadTags;$('#clear-tags').onclick=()=>{activeTags.clear();loadTags()};
async function loadCases(){const rows=await api('/api/samples');const dsSel=$('#case-dataset');const datasets=[...new Set(rows.map(r=>groupName(r.group)))];const cur=dsSel.value;dsSel.innerHTML='<option value="">全データセット</option>'+datasets.map(d=>`<option value="${esc(d)}" ${d===cur?'selected':''}>${esc(d)}</option>`).join('');
const v=$('#case-verdict').value;let shown=rows;if(dsSel.value)shown=shown.filter(r=>groupName(r.group)===dsSel.value);if(v)shown=shown.filter(r=>r.verdict===v);
const groups=new Map();shown.forEach(r=>{const k=`${groupName(r.group)} / ${catName(caseCategory(r))}`;if(!groups.has(k))groups.set(k,[]);groups.get(k).push(r)});
$('#cases').innerHTML=groups.size?[...groups.entries()].sort((a,b)=>a[0].localeCompare(b[0],'ja')).map(([k,items])=>{const ok=items.filter(x=>x.verdict==='OK').length,ng=items.filter(x=>x.verdict==='NG').length,rv=items.filter(x=>x.verdict==='REVIEW').length;return`<div class="case-section"><h3>${esc(k)}</h3><p class="muted">${items.length}件 (OK ${ok} / REVIEW ${rv} / NG ${ng})</p>${items.map(sampleCard).join('')}</div>`}).join(''):'対象なし — デモ実行でサンプルが登録されます'}
$('#reload-cases').onclick=loadCases;$('#case-dataset').onchange=loadCases;$('#case-verdict').onchange=loadCases;
$('#reload-reviews').onclick=loadReviews;$('#review-status').onchange=loadReviews;$('#reload-models').onclick=loadModels;$('#reload-metrics').onclick=loadMetrics;
$('#train-reference').onclick=async()=>{await api('/api/learning/reference?product_id=demo_press_part',{method:'POST'});alert('候補学習を登録しました。自動昇格はしません。');setTimeout(loadModels,2500)};
