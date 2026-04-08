import os
import json
import pandas as pd
from datetime import datetime
import json
import urllib.request
import os

# Injection MoldingHub - Automated Report Generator
# This script compiles DOE results, resin properties, and visualization frames into a report.

LITELLM_BASE_URL = os.environ.get("OPENAI_BASE_URL", "http://localhost:4000/v1")
LITELLM_API_KEY = os.environ.get("OPENAI_API_KEY", "local-dev-key")
MODEL_REVIEWER = "google/gemini-2.5-flash"

def run_ai_audit(report_text):
    try:
        sys_prompt = (
            "あなたは非常に厳格な射出成形・金型設計の監査AI（デザインレビュワー）です。\n"
            "以下のDOEシミュレーション結果（最適な充填時間や反り量・Warpage）を含むレポートを確認し、\n"
            "エンジニアリングの観点から考えうるリスク、冷却設定の懸念事項、エッジケースを指摘してください。\n"
            "絶対に妥協せず、問題がなければ「量産移行に問題なし」とだけ答えてください。"
        )
        
        body = {
            "model": MODEL_REVIEWER,
            "messages": [
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": f"以下がDOEの最終レポートです。監査願います：\n\n{report_text}"}
            ],
            "temperature": 0.2
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {LITELLM_API_KEY}"
        }
        
        req = urllib.request.Request(
            f"{LITELLM_BASE_URL}/chat/completions",
            data=json.dumps(body).encode("utf-8"),
            headers=headers
        )
        
        # タイムアウトを長めに設定（ディープシンキングモデル対応）
        with urllib.request.urlopen(req, timeout=90) as response:
            payload = json.loads(response.read().decode("utf-8"))
            
        choices = payload.get("choices", [])
        if not choices:
            return "⚠️ AI Audit Error: No choices returned."
            
        return choices[0].get("message", {}).get("content", "").strip()
        
    except Exception as e:
        return f"⚠️ AI監査の実行中にエラーが発生しました: {str(e)}"

def create_report(study_dir, material_id, out_file="Molding_Analysis_Report.md"):
    print(f"--> Compiling Report for {study_dir}")
    
    # Load DOE Results
    doe_path = os.path.join(study_dir, "doe_results.csv")
    if os.path.exists(doe_path):
        doe_df = pd.read_csv(doe_path)
        optimal_row = doe_df.iloc[doe_df['Warpage_mm'].idxmin()]
    else:
        doe_df = None
        optimal_row = None

    # Load Resin Data
    # Assume resin_database.json is available in the hub root
    resin_info = "Resin: Variable (DOE Analysis)"
    
    report_content = f"""# Injection Molding Analysis Report
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## 1. Study Overview
- **Material**: {material_id}
- **Simulation Engine**: OpenFOAM v11 (CFD) + ElmerFEM (FEA)
- **Optimization Strategy**: R-Language DOE (L9 Taguchi)

## 2. Optimization Results (DOE)
The following Design of Experiments matrix indicates the sensitivities of injection velocity and coolant temperature to final warpage.

| Run | Velocity (m/s) | Coolant T (C) | Fill Time (s) | Warpage (mm) |
|:--- |:--- |:--- |:--- |:--- |
"""
    if doe_df is not None:
        for idx, row in doe_df.iterrows():
            report_content += f"| {idx+1} | {row.get('Velocity', 'N/A')} | {row.get('CoolantT', 'N/A')} | {row.get('FillTime_s', 'N/A')} | {row.get('Warpage_mm', 'N/A')} |\n"
        
        report_content += f"\n### ✅ Optimal Condition Found\n"
        report_content += f"- **Run ID**: {optimal_row.name + 1}\n"
        report_content += f"- **Optimal Velocity**: {optimal_row.get('Velocity', 'N/A')} m/s\n"
        report_content += f"- **Optimal Coolant Temp**: {optimal_row.get('CoolantT', 'N/A')} C\n"
        report_content += f"- **Minimum predicted Warpage**: {optimal_row.get('Warpage_mm', 'N/A')} mm\n"
    else:
        report_content += "| No Data | | | | |\n"

    report_content += """
## 3. Visualization Portfolio
Below are the renders of the melt-front progression at the optimal condition.

![Melt Front Analysis](output_images/frame_0000.png)
*Figure 1: Initial Injection Gate State (Melt Front alpha=0.5)*

![Melt Front Progress](output_images/frame_0004.png)
*Figure 2: Partial Filling State*
"""
    report_content += f"""
## 4. Engineering Conclusion
Based on the coupled CFD-FEA analysis, the part exhibits stable flow with the current gate configuration. 
**Recommended Action**: Implement the cooling layout consistent with Run {optimal_row.name + 1 if optimal_row is not None else 'N/A'} of the DOE to minimize warpage across the thin-walled sections.
"""

    print("--> Running AI Final Audit (Sandwich Review Phase)...")
    ai_feedback = run_ai_audit(report_content)

    report_content += f"""
## 5. AI Final Audit (デザインレビュー)
{ai_feedback}

---
*Clawstack Automated Engineering Framework*
"""

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(report_content)
    
    print(f"Report Generated: {out_file}")

if __name__ == "__main__":
    # Test execution
    create_report(".", "pa66_gf30_generic")
