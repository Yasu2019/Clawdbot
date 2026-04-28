import React from 'react';
import HeroAurora from '@/components/hero/HeroAurora';

const DOMAINS = [
  {
    title: "1. Operations & Systems",
    items: [
      { name: "Ops Toolbox", href: "http://localhost:8088/apps/operations_toolbox/index.html", description: "Maintenance & Status." },
      { name: "n8n Automation", href: "http://localhost:5679", description: "Workflow orchestration." },
    ]
  },
  {
    title: "2. Quality & Compliance",
    items: [
      { name: "IATF Rails", href: "http://localhost:3004/users/sign_in", description: "Core compliance system." },
      { name: "Quality Dashboard", href: "http://localhost:8090", description: "FMEA/QIF analytics." },
      { name: "視覚AI品質検査", href: "http://localhost:8095", description: "外観検査・不良候補検出 (Gemini Vision)." },
      { name: "IATF動画工場", href: "http://localhost:8088/apps/iatf_video_factory/status.html", description: "内部監査教材3D動画 自律生成 (Blender+VoiceVox)." },
      { name: "IATF動画エディタ", href: "http://localhost:8096", description: "AI生成動画をタイムスタンプ指定で自然言語編集." },
    ]
  },
  {
    title: "3. Geometry & 3D Workbench",
    items: [
      { name: "3D Workbench", href: "http://localhost:8088/apps/three_d_workbench/index.html", description: "CAD/Blender library." },
      { name: "GD&T Overlay", href: "http://localhost:8088/apps/gdt_overlay_studio/index.html", description: "Datum visualization." },
    ]
  },
  {
    title: "4. CAE & Dynamics",
    items: [
      { name: "OpenRadioss", href: "http://localhost:8088/apps/radioss_hub/index.html", description: "Crash simulation." },
      { name: "Molding Hub", href: "http://localhost:8088/apps/molding_hub/index.html", description: "ElmerFEM cockpit." },
      { name: "DesignCAE Loop", href: "http://localhost:8088/apps/design_cae_loop/index.html", description: "金型・DOE・CAE・ノウハウ蓄積ループ." },
    ]
  },
  {
    title: "5. Data Ingestion & RAG",
    items: [
      { name: "OpenCode GO Intel", href: "http://localhost:8088/apps/opencode_go/portal_card/index.html", description: "外部AI情報収集・採用判定レイヤー." },
      { name: "Ingestion / RAG Hub", href: "http://localhost:8088/apps/ingestion_rag_control_center/index.html", description: "Monitor sync health." },
      { name: "Paperless NGX", href: "http://localhost:8000", description: "Document OCR store." },
    ]
  },
  {
    title: "6. Autonomous Learning",
    items: [
      { name: "K10 自律ノウハウ蓄積", href: "http://localhost:8088/apps/k10_learning/index.html", description: "公開情報調査・有益性判定・DB登録 (OpenCode GO)." },
      { name: "Learning Memory", href: "http://localhost:8088/apps/learning_memory/index.html", description: "RL feedback memory." },
      { name: "AI Strategy Scout", href: "http://localhost:8088/apps/ai_strategy_scout/index.html", description: "Daily tactic collection." },
      { name: "AI Governance Hub", href: "http://localhost:8088/apps/paperclip_governance/index.html", description: "Org chart & budget control." },
    ]
  }
];

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-neutral-950 text-white selection:bg-white/10">
      <HeroAurora 
        title="Engineering Portal を、意思を持つ UI へ。"
        subtitle="React Bits を導入し、静的だったポータルを実務性能を維持したまま先進的な体験へと進化させます。これは Clawstack V3 へ向けた最初のステップです。"
      >
        <a 
          href="http://localhost:18789" 
          className="rounded-2xl bg-white px-6 py-3 text-sm font-semibold text-black hover:bg-white/90 transition-colors"
        >
          OpenClaw Chat を開く
        </a>
        <a 
          href="http://localhost:8088/portal.html" 
          className="rounded-2xl border border-white/20 px-6 py-3 text-sm font-semibold text-white hover:bg-white/5 transition-colors"
        >
          従来のポータルに戻る
        </a>
      </HeroAurora>

      <div className="mx-auto max-w-6xl px-6 py-24 space-y-24">
        {DOMAINS.map((domain, idx) => (
          <section key={idx} className="space-y-8">
            <h2 className="text-xs font-bold uppercase tracking-[0.2em] text-white/40 border-b border-white/5 pb-4">
              {domain.title}
            </h2>
            <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
              {domain.items.map((item, itemIdx) => (
                <a 
                  key={itemIdx}
                  href={item.href}
                  className="group block rounded-3xl border border-white/10 bg-white/[0.02] p-8 hover:bg-white/[0.05] hover:border-white/20 transition-all duration-300"
                >
                  <h3 className="text-xl font-semibold mb-2 group-hover:translate-x-1 transition-transform duration-300">
                    {item.name}
                  </h3>
                  <p className="text-sm text-white/50 leading-relaxed">
                    {item.description}
                  </p>
                </a>
              ))}
            </div>
          </section>
        ))}
      </div>

      <footer className="border-t border-white/5 py-12 px-6">
        <div className="mx-auto max-w-6xl text-center text-xs text-white/30">
          <p>© 2026 Clawstack Engineering System. Powered by React Bits Protocol.</p>
        </div>
      </footer>
    </main>
  );
}
