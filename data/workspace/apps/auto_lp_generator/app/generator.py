from pathlib import Path
from pydantic import BaseModel, Field
from datetime import datetime
import html, re, json
BASE_DIR = Path(__file__).resolve().parent
GENERATED_DIR = BASE_DIR / "generated"
GENERATED_DIR.mkdir(exist_ok=True)

class LPRequest(BaseModel):
    title: str = "品質保証ダッシュボード"
    subtitle: str = "製造現場の状況を、顧客・監査員・社内責任者に分かりやすく説明します。"
    theme: str = "quality_dashboard"
    target: str = "製造業の品質責任者"
    tone: str = "工業的、信頼感、ブルー基調、ミニマル"
    sections: list[str] = Field(default_factory=lambda:["KPIサマリー","工程フロー","不良率の推移","是正処置フロー","問い合わせ"])
    company_name: str = "ミツイ精密株式会社"
    output_name: str | None = None
    notes: str = ""

def slugify(s: str) -> str:
    return (re.sub(r"[^a-zA-Z0-9_\-]+", "_", s).strip("_") or "lp")[:80]

def section_html(name: str) -> str:
    e=html.escape(name)
    if "KPI" in name or "サマリー" in name:
        return f'''<section class="section"><div class="section-title">{e}</div><div class="kpi-grid"><div class="kpi"><span>不良率</span><strong>0.38%</strong><small>前月比 -0.12pt</small></div><div class="kpi"><span>検査進捗</span><strong>96.4%</strong><small>ピークFC対応可否を確認</small></div><div class="kpi"><span>是正完了</span><strong>14/16</strong><small>期限超過 0件</small></div></div></section>'''
    if "工程" in name or "フロー" in name:
        return f'''<section class="section"><div class="section-title">{e}</div><div class="flow"><div>受入</div><div>プレス</div><div>洗浄</div><div>外観検査</div><div>出荷承認</div></div><p class="muted">各工程の入力・出力・管理項目・異常時対応を1画面で説明できます。</p></section>'''
    if "不良" in name or "推移" in name or "グラフ" in name:
        return f'''<section class="section"><div class="section-title">{e}</div><div class="chart"><div style="height:30%"></div><div style="height:55%"></div><div style="height:42%"></div><div style="height:70%"></div><div style="height:38%"></div></div><p class="muted">実運用ではSQL Server / CSV / OpenClaw RAGから取得したデータに差し替えます。</p></section>'''
    return f'''<section class="section"><div class="section-title">{e}</div><p>{e} に関する説明、判断基準、証拠資料、次アクションを整理します。</p></section>'''

def generate_lp(req: LPRequest):
    now=datetime.now().strftime("%Y%m%d_%H%M%S")
    filename=f"{now}_{slugify(req.output_name or req.title)}.html"
    path=GENERATED_DIR/filename
    sections="\n".join(section_html(s) for s in req.sections)
    page=f'''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{html.escape(req.title)}</title><style>
:root{{--bg:#07111f;--panel:#0f1f35;--panel2:#132944;--text:#eaf2ff;--muted:#9fb4d1;--line:#29435f;--accent:#58a6ff;--accent2:#7dd3fc}}*{{box-sizing:border-box}}body{{margin:0;font-family:system-ui,-apple-system,"Segoe UI",sans-serif;background:radial-gradient(circle at 15% 10%,rgba(88,166,255,.25),transparent 28%),linear-gradient(135deg,#07111f 0%,#0a1728 55%,#081320 100%);color:var(--text)}}.hero{{padding:64px 7vw 38px}}.badge{{display:inline-block;border:1px solid var(--line);color:var(--accent2);padding:7px 12px;border-radius:999px;background:rgba(255,255,255,.04)}}h1{{font-size:clamp(34px,5vw,72px);line-height:1.05;margin:22px 0 16px;letter-spacing:-.04em}}.lead{{max-width:880px;color:var(--muted);font-size:clamp(16px,2vw,22px);line-height:1.75}}.cta{{margin-top:28px;display:flex;gap:14px;flex-wrap:wrap}}.btn{{padding:13px 18px;border-radius:14px;border:1px solid var(--line);color:var(--text);text-decoration:none;background:rgba(88,166,255,.16)}}.btn.primary{{background:linear-gradient(135deg,var(--accent),#2563eb);border:none}}.meta{{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px;padding:0 7vw 28px}}.meta-card{{background:rgba(15,31,53,.75);border:1px solid var(--line);border-radius:22px;padding:18px}}.wrap{{padding:20px 7vw 80px;display:grid;gap:20px}}.section{{background:rgba(15,31,53,.82);border:1px solid var(--line);border-radius:28px;padding:26px;box-shadow:0 18px 60px rgba(0,0,0,.28)}}.section-title{{font-size:24px;font-weight:800;margin-bottom:16px}}.kpi-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:14px}}.kpi{{background:var(--panel2);border:1px solid var(--line);border-radius:20px;padding:18px}}.kpi span{{color:var(--muted);display:block}}.kpi strong{{display:block;font-size:34px;margin:8px 0}}.kpi small,.muted{{color:var(--muted);line-height:1.7}}.flow{{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:12px}}.flow div{{text-align:center;padding:16px;border-radius:16px;background:linear-gradient(135deg,rgba(88,166,255,.25),rgba(125,211,252,.08));border:1px solid var(--line)}}.chart{{height:220px;display:flex;gap:12px;align-items:end;border-left:1px solid var(--line);border-bottom:1px solid var(--line);padding:18px}}.chart div{{flex:1;min-height:18%;border-radius:12px 12px 0 0;background:linear-gradient(180deg,var(--accent2),#2563eb)}}.footer{{padding:34px 7vw;color:var(--muted);border-top:1px solid var(--line)}}
</style></head><body><header class="hero"><span class="badge">{html.escape(req.company_name)} / Auto LP Generator</span><h1>{html.escape(req.title)}</h1><p class="lead">{html.escape(req.subtitle)}</p><div class="cta"><a class="btn primary" href="#main">内容を見る</a><a class="btn" href="#contact">相談・レビュー</a></div></header><div class="meta"><div class="meta-card"><b>対象</b><br>{html.escape(req.target)}</div><div class="meta-card"><b>トンマナ</b><br>{html.escape(req.tone)}</div><div class="meta-card"><b>テーマ</b><br>{html.escape(req.theme)}</div></div><main id="main" class="wrap">{sections}<section class="section" id="contact"><div class="section-title">生成メモ</div><p class="muted">{html.escape(req.notes) or 'Image2 / Claude Design / Claude Codeでブラッシュアップする前提の初期LPです。'}</p></section></main><footer class="footer">Generated by OpenClaw Auto LP Generator / {now}</footer></body></html>'''
    path.write_text(page, encoding='utf-8')
    manifest={"filename":filename,"path":str(path),"url":f"/generated/{filename}","created_at":now,"request":req.model_dump()}
    (GENERATED_DIR/f"{filename}.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    return manifest

def list_outputs():
    return {"files":[{"filename":p.name,"url":f"/generated/{p.name}","size":p.stat().st_size,"mtime":p.stat().st_mtime} for p in sorted(GENERATED_DIR.glob('*.html'), reverse=True)]}
