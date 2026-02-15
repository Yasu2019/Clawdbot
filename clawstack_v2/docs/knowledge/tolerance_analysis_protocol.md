# Clawdbot 自走プロトコル: FreeCAD公差解析ツール完成

## 🎯 目標

FreeCAD公差解析ツール（Cetol6Sigma風）をantigravityコンテナ上で完全動作させる

---

## 📁 既存ファイル

```
/work/freecad/tolerance_analysis/
├── __init__.py
├── ToleranceAnalysis.FCMacro
├── cli.py
├── core/
│   ├── data_model.py
│   ├── calculator.py
│   └── reporter.py
├── engines/
│   ├── base_engine.py
│   ├── dxf_engine.py
│   ├── step_engine.py
│   └── stl_engine.py
└── ui/
    ├── main_panel.py
    ├── model_tree.py
    ├── advisor.py
    └── plots.py
```

---

## ✅ タスクリスト

### 1. CLIデモ動作確認 (完了済み)

```bash
docker exec clawstack-antigravity-1 python3 /work/freecad/tolerance_analysis/cli.py demo
```

### 2. FreeCAD Part モジュールでSTEP読み込みテスト

```bash
# FreeCAD Python経由でPartモジュール確認
docker exec clawstack-antigravity-1 /opt/freecad/AppRun python3 << 'EOF'
import sys
sys.path.insert(0, '/work/freecad')
import FreeCAD
import Part
print(f"FreeCAD Version: {FreeCAD.Version()}")

# Create test box
box = Part.makeBox(100, 50, 20)
print(f"Volume: {box.Volume} mm³")
print(f"Faces: {len(box.Faces)}")
print(f"Edges: {len(box.Edges)}")
print("✅ FreeCAD Part module OK")
EOF
```

### 3. サンプルSTEPファイル作成とテスト

```bash
# FreeCADでSTEPファイル生成
docker exec clawstack-antigravity-1 /opt/freecad/AppRun python3 << 'EOF'
import sys
sys.path.insert(0, '/work/freecad')
import FreeCAD
import Part

# Create sample assembly
doc = FreeCAD.newDocument("TestAssembly")

# Create shaft
shaft = Part.makeCylinder(25, 100)
shaft_obj = doc.addObject("Part::Feature", "Shaft")
shaft_obj.Shape = shaft

# Create housing
housing = Part.makeCylinder(30, 80)
housing.translate(FreeCAD.Vector(0, 0, 10))
housing_obj = doc.addObject("Part::Feature", "Housing")
housing_obj.Shape = housing

# Export STEP
Part.export([shaft_obj, housing_obj], "/work/freecad/test_assembly.step")
print("✅ Created /work/freecad/test_assembly.step")
EOF
```

### 4. STEPエンジンでファイル読み込み

```bash
docker exec clawstack-antigravity-1 /opt/freecad/AppRun python3 << 'EOF'
import sys
sys.path.insert(0, '/work/freecad')

from tolerance_analysis.engines.step_engine import STEPEngine, load_step

# Load STEP file
try:
    part = load_step("/work/freecad/test_assembly.step", default_tolerance=0.05)
    print(f"Part: {part.name}")
    print(f"Dimensions: {len(part.dimensions)}")
    print(f"Features: {len(part.features)}")
    
    for dim in part.dimensions[:5]:
        print(f"  - {dim.name}: {dim.nominal:.3f} ±{dim.tolerance.bilateral:.4f}")
    
    print("✅ STEP engine OK")
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
EOF
```

### 5. 完全解析パイプライン実行

```bash
docker exec clawstack-antigravity-1 /opt/freecad/AppRun python3 << 'EOF'
import sys
sys.path.insert(0, '/work/freecad')

from tolerance_analysis.engines.step_engine import load_step
from tolerance_analysis.core.data_model import Chain, ChainDirection
from tolerance_analysis.core.calculator import ToleranceCalculator
from tolerance_analysis.core.reporter import ToleranceReporter

# Load STEP
part = load_step("/work/freecad/test_assembly.step", default_tolerance=0.025)
print(f"Loaded: {part.name} ({len(part.dimensions)} dimensions)")

# Create tolerance chain
chain = Chain(name="Shaft-Housing Fit")
for dim in part.dimensions[:5]:
    chain.add_dimension(dim)

# Analyze
calc = ToleranceCalculator(sigma=3.0, mc_samples=10000)
result = calc.analyze(chain)

print("\n=== Analysis Result ===")
print(f"Nominal: {result.nominal:.4f} mm")
print(f"Worst Case: ±{result.wc_range/2:.4f} mm")
print(f"RSS (3σ): ±{result.rss_range/2:.4f} mm")
print(f"Monte Carlo: {result.mc_lower:.4f} ~ {result.mc_upper:.4f} mm")

# Generate report
reporter = ToleranceReporter(output_dir="/work/freecad/reports")
html = reporter.generate_html(chain, result)
print(f"\n📄 Report: {html}")
print("✅ Full pipeline OK")
EOF
```

### 6. HTMLレポート確認

```bash
docker exec clawstack-antigravity-1 cat /work/freecad/reports/tolerance_report_*.html | head -100
```

---

## 🔧 トラブルシューティング

### FreeCAD import エラー時

```bash
# AppImage内Pythonを使用
docker exec clawstack-antigravity-1 /opt/freecad/AppRun python3 -c "import FreeCAD; print('OK')"
```

### ezdxf not found

```bash
docker exec clawstack-antigravity-1 pip3 install ezdxf
```

### numpy/scipy missing

```bash
docker exec clawstack-antigravity-1 pip3 install numpy scipy
```

---

## 📊 成功基準

1. ✅ CLI demo 実行完了
2. ✅ FreeCAD Part モジュール動作
3. ✅ STEP ファイル作成・読み込み
4. ✅ 公差解析パイプライン実行
5. ✅ HTML レポート生成

---

## 📝 完了報告フォーマット

```
## FreeCAD公差解析ツール 完了報告

### 実行結果
- CLI Demo: ✅/❌
- STEP Engine: ✅/❌
- Full Pipeline: ✅/❌
- Report Generated: [path]

### 解析サンプル
- 公称値: X.XXX mm
- Worst Case: ±X.XXX mm
- RSS (3σ): ±X.XXX mm

### 発生した問題と対処
- [あれば記載]
```
