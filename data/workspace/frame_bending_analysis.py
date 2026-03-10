"""
Frame Bending Analysis - Simplified Beam Model
================================================
Scenario: Punch pushes Product downward (Z-) through Frame hole.
Product is still partially connected to Frame.
Frame is supported by Guide ledges (0.2mm step) on both sides.

Model: Simply-supported beam with center point load.
"""
import numpy as np

# === Material Properties: Ni201 (Pure Nickel) ===
E = 207e3      # Young's modulus [MPa] = 207 GPa
sigma_y = 103  # Yield stress (annealed) [MPa]
sigma_uts = 403  # Ultimate tensile stress [MPa]

# === Geometry ===
t = 0.2        # Frame (and Product) thickness [mm]

# Frame strip dimensions (from 品質仕様書 drawing)
frame_width_Y = 13.15   # Frame strip width in Y direction [mm]
hole_height_Y = 2.10    # Hole height in Y direction [mm]
hole_width_X = 5.0      # Hole width in X direction [mm]

# Punch force
F = 1.2  # [N] - punching/push-out resistance

# === Guide Contact Geometry ===
# From the image: Guide supports Frame via 0.2mm step ledges on both sides
# The unsupported span depends on the Guide geometry
# Let's calculate for several possible spans based on the visible geometry

print("=" * 70)
print("Frame Bending Analysis - Ni201 t=0.2mm, F=1.2N")
print("=" * 70)
print(f"\nMaterial: Ni201 (E={E/1e3:.0f} GPa, σy={sigma_y} MPa, σuts={sigma_uts} MPa)")
print(f"Frame thickness: {t} mm")
print(f"Punch push-out force: {F} N")
print()

# ===================================================================
# Case 1: X-direction bending (across the feed direction)
# The Frame bridges across the Guide support in X
# Span = distance between inner edges of Guide ledges
# ===================================================================
print("-" * 70)
print("ANALYSIS: Frame bending in X-direction (across feed)")
print("-" * 70)

# The beam width (in Y) that carries the load is the "bridge" material
# around the hole. On each side of the hole in Y:
# bridge_Y = (frame_width_Y - hole_height_Y) / 2
bridge_Y = (frame_width_Y - hole_height_Y) / 2
print(f"\nFrame bridge width (Y): ({frame_width_Y} - {hole_height_Y})/2 = {bridge_Y:.2f} mm each side")
print(f"Total beam width carrying load: 2 × {bridge_Y:.2f} = {2*bridge_Y:.2f} mm")
b = 2 * bridge_Y  # Total effective beam width

# Try multiple spans
spans_X = [3.0, 4.0, 5.0, 6.0, 7.0, 8.0]  # [mm]

print(f"\n{'Span L':>8} {'I':>12} {'δ_max':>10} {'σ_max':>10} {'σ/σy':>8} {'Status':>12}")
print(f"{'(mm)':>8} {'(mm⁴)':>12} {'(mm)':>10} {'(MPa)':>10} {'':>8} {'':>12}")
print("-" * 72)

for L in spans_X:
    # Moment of inertia: I = b * t³ / 12
    I = b * t**3 / 12
    
    # Simply-supported beam, center point load
    # Max deflection: δ = F*L³ / (48*E*I)
    delta_max = F * L**3 / (48 * E * I)
    
    # Max bending stress: σ = M*c/I, where M = F*L/4, c = t/2
    M_max = F * L / 4  # [N·mm]
    sigma_max = M_max * (t/2) / I  # [MPa]
    
    ratio = sigma_max / sigma_y
    if ratio < 0.5:
        status = "🟢 安全"
    elif ratio < 1.0:
        status = "🟡 注意"
    else:
        status = "🔴 降伏"
    
    print(f"{L:8.1f} {I:12.6f} {delta_max:10.6f} {sigma_max:10.2f} {ratio:8.2f} {status:>12}")

# ===================================================================
# Most likely scenario: span ≈ 5mm (hole width)
# ===================================================================
print("\n" + "=" * 70)
print("DETAILED ANALYSIS: Span = 5.0mm (Hole Width)")
print("=" * 70)

L = 5.0  # [mm]
I = b * t**3 / 12
delta = F * L**3 / (48 * E * I)
M = F * L / 4
sigma = M * (t/2) / I

print(f"\n  Span (L):           {L} mm")
print(f"  Beam width (b):     {b:.2f} mm")
print(f"  Thickness (t):      {t} mm")
print(f"  I (inertia):        {I:.8f} mm⁴")
print(f"  Max deflection:     {delta:.6f} mm = {delta*1000:.3f} μm")
print(f"  Max bending stress: {sigma:.2f} MPa")
print(f"  Yield ratio:        {sigma/sigma_y:.2f} ({sigma/sigma_y*100:.1f}% of yield)")
print(f"  Step height:        0.2 mm")
print(f"  δ vs step height:   {delta:.6f} / 0.2 = {delta/0.2*100:.4f}%")

# ===================================================================
# Force comparison: separation vs bending
# ===================================================================
print("\n" + "=" * 70)
print("FORCE COMPARISON: Product separation vs Frame deformation")
print("=" * 70)

# Force to cause yield in the frame beam
# σy = M*c/I = F_y*L/(4) * (t/2) / I
# F_y = σy * I * 4 / (L * t/2)
F_yield = sigma_y * I * 4 / (L * t/2)
F_uts = sigma_uts * I * 4 / (L * t/2)

print(f"\n  Push-out force (given):     {F:.2f} N")
print(f"  Force to YIELD Frame:      {F_yield:.2f} N")
print(f"  Force to FRACTURE Frame:   {F_uts:.2f} N")
print(f"  ")
print(f"  F_push / F_yield = {F/F_yield:.4f} ({F/F_yield*100:.2f}%)")

if F < F_yield:
    print(f"\n  ✅ 結論: プッシュ力 ({F}N) < フレーム降伏力 ({F_yield:.2f}N)")
    print(f"  → フレームは弾性変形範囲内。弓状変形は極めて小さい。")
    print(f"  → 変形量 {delta:.6f} mm はステップ高さ 0.2mm の {delta/0.2*100:.4f}% → 無視可能")
    
    if delta < 0.01:  # Less than 10 microns
        print(f"\n  📌 結論: Productはフレームが変形する前に、Frameから抜け落ちる可能性が高い。")
        print(f"     Frameの弾性変形 ({delta*1000:.1f} μm) は抵抗としてほぼ無視できるレベル。")
else:
    print(f"\n  ⚠️ 結論: プッシュ力 ({F}N) ≥ フレーム降伏力 ({F_yield:.2f}N)")
    print(f"  → フレームが塑性変形（弓状変形）する可能性あり。")

# ===================================================================
# Additional: Deflection at yield for comparison
# ===================================================================
delta_at_yield = F_yield * L**3 / (48 * E * I)
print(f"\n  参考: 降伏時の変形量: {delta_at_yield:.4f} mm = {delta_at_yield*1000:.1f} μm")

# ===================================================================
# Product-Frame shear analysis
# ===================================================================
print("\n" + "=" * 70)
print("SHEAR ANALYSIS: Product-Frame connection (残留接合部)")
print("=" * 70)

# After punching, the Product may still have micro-bridges (バリ/接合部)
# connecting it to the Frame. The shear area is the perimeter × thickness.
# Perimeter of Product in the hole
perimeter = 2 * (hole_width_X + hole_height_Y)  # approximate rectangle
print(f"\n  Product perimeter:   {perimeter:.2f} mm")
print(f"  Thickness:           {t} mm")

# If fully connected (not yet punched)
shear_strength = sigma_uts * 0.6  # Approximate shear = 60% of UTS
shear_area = perimeter * t
F_shear_full = shear_strength * shear_area

print(f"  Shear strength:      {shear_strength:.0f} MPa (≈60% UTS)")
print(f"  Full shear area:     {shear_area:.2f} mm²")
print(f"  Full shear force:    {F_shear_full:.1f} N")

# But post-punching, the connection is mostly severed. 
# The 1.2N represents the residual connection/friction.
# We compare this with the frame bending stiffness.

# Spring rate of the frame beam
k_beam = 48 * E * I / L**3  # [N/mm]
print(f"\n  Frame beam stiffness: {k_beam:.2f} N/mm")
print(f"  Deflection per 1N:    {1/k_beam:.6f} mm = {1/k_beam*1000:.3f} μm/N")
print(f"  Deflection at 1.2N:   {F/k_beam:.6f} mm = {F/k_beam*1000:.3f} μm")
print(f"\n  ✅ フレームのばね定数は非常に高い ({k_beam:.0f} N/mm)")
print(f"  → 1.2N ではほとんど変形しない")
print(f"  → Productはフレームから抜け落ちる方が先")
