# Stitch Priority Targets (2026-04-04)

## Priority Order

1. `Portal TOP`
   - Reason: visual整理と導線改善の効果が最も大きい
   - Stitch role: card grouping, header hierarchy, category blocks, visual rhythm
   - Codex role: actual links, health indicators, integration, responsive adjustments

2. `Ingestion / RAG Control Center`
   - Reason: 情報量が多く、状態表示と導線の整理余地が大きい
   - Stitch role: KPI card hierarchy, warning banner layout, grouped entry blocks
   - Codex role: JSON wiring, alert rules, real status integration

3. `Note Pro`
   - Reason: recommendation rail + editor + assistant sidebar の構成改善が効く
   - Stitch role: article recommendation cards, editor shell, assistant panel layout
   - Codex role: digest loading, prompt generation, export behavior

4. `Open Notebook → Obsidian`
   - Reason: 運用説明ハブとして見た目の説得力が出しやすい
   - Stitch role: flow explanation, panels, visual onboarding
   - Codex role: actual commands, links, safe workflow rules

## Use With Caution

- `Learning Memory`
- `Email Search`
- `Storage Cleanup Review`
- `FMEA / FTA / Why-Why` launcher pages

Reason:
- layout drafts are useful
- but real data, safe actions, and operational detail must remain Codex-owned

## Avoid Stitch

- `IATF Rails` business screens
- `QMS Audit` decision logic screens
- `3D Converter / GD&T / DXF` production work surfaces
- `Paperless / Gmail / RAG` core control surfaces

Reason:
- operational accuracy matters more than visual novelty
- high risk of drift between mock and implementation

## Decision Rule

- If the screen is mostly navigation, onboarding, summary, or explanation -> Stitch first
- If the screen performs irreversible action, backend control, or domain judgment -> Codex first
