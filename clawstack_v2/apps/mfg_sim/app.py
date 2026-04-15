import io
import math
from dataclasses import dataclass

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st


st.set_page_config(
    page_title="Manufacturing Engineering Simulator Pro",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =========================================================
# Data models / presets
# =========================================================

@dataclass
class MaterialPreset:
    name: str
    young_gpa: float
    yield_mpa: float
    thermal_expansion_ppm: float
    density_g_cm3: float
    note: str


METAL_PRESETS = {
    "A1050-H24": MaterialPreset("A1050-H24", 69.0, 110.0, 23.6, 2.71, "アルミ母材の簡易代表値"),
    "A5052-H34": MaterialPreset("A5052-H34", 70.0, 215.0, 23.8, 2.68, "アルミ系の比較用"),
    "Cu (C1100)": MaterialPreset("Cu (C1100)", 110.0, 220.0, 16.5, 8.96, "銅母材の簡易代表値"),
    "SPCC": MaterialPreset("SPCC", 210.0, 270.0, 11.7, 7.85, "鋼板の簡易代表値"),
}

PLATING_PRESETS = {
    "Sn": {"melt_c": 232.0, "cte_ppm": 22.0, "young_gpa": 50.0},
    "Ni": {"melt_c": 1455.0, "cte_ppm": 13.0, "young_gpa": 200.0},
    "Cu": {"melt_c": 1085.0, "cte_ppm": 16.5, "young_gpa": 110.0},
}

RESIN_PRESETS = {
    "PP": {"melt_temp_c": 220, "base_viscosity": 1.00, "mold_shrink_pct": 1.8, "fiber_factor": 0.2},
    "ABS": {"melt_temp_c": 240, "base_viscosity": 1.15, "mold_shrink_pct": 0.6, "fiber_factor": 0.1},
    "PA6-GF30": {"melt_temp_c": 280, "base_viscosity": 1.40, "mold_shrink_pct": 0.4, "fiber_factor": 0.8},
}


# =========================================================
# Utility functions
# =========================================================

def clamp(x, lo, hi):
    return max(lo, min(hi, x))


def logistic(x, x0=0.0, k=1.0):
    return 1.0 / (1.0 + math.exp(-k * (x - x0)))


def add_disclaimer():
    st.caption(
        "注意: 本アプリは教育・仮説整理・会議説明用の簡易モデルです。"
        "厳密設計、顧客提出、保証判断には実測・CAE・材料データ・工程データと併用してください。"
    )


def section_title(text):
    st.markdown(f"### {text}")


def plot_single(x, ys, labels, xlabel, ylabel, title):
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for y, label in zip(ys, labels):
        ax.plot(x, y, label=label)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, alpha=0.3)
    if len(labels) > 1:
        ax.legend()
    st.pyplot(fig)


def overlay_csv_plot(df, x_col, y_cols, title, xlabel, ylabel):
    fig, ax = plt.subplots(figsize=(8, 4.2))
    for col in y_cols:
        if col in df.columns:
            ax.plot(df[x_col], df[col], marker="o", label=col)
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.3)
    ax.legend()
    st.pyplot(fig)


def load_csv(uploaded):
    try:
        return pd.read_csv(uploaded)
    except Exception:
        uploaded.seek(0)
        return pd.read_excel(uploaded)


# =========================================================
# Sidebar
# =========================================================

st.title("Manufacturing Engineering Simulator Pro")
add_disclaimer()

with st.sidebar:
    st.header("共通設定")
    show_formulas = st.toggle("近似式を表示", value=True)
    show_limits = st.toggle("前提・限界を表示", value=True)
    language = st.selectbox("表示補助", ["日本語", "English keywords mixed"], index=0)
    st.markdown("---")
    st.write("このZIPは Claude / Codex に渡して、さらなる高度化の土台として使えるよう構成しています。")

tabs = st.tabs([
    "1. 射出成形",
    "2. 金属プレス・スプリングバック",
    "3. レベラー概念",
    "4. 母材＋めっき＋リフロー",
    "5. Niストライク比較",
    "6. IMC成長",
    "7. CSV実測重ね表示",
    "8. プロトコル/前提"
])


# =========================================================
# 1. Injection Molding
# =========================================================
with tabs[0]:
    section_title("射出成形: 充填・ヒケ・ショート・バリ・反り")
    resin_name = st.selectbox("樹脂プリセット", list(RESIN_PRESETS.keys()), index=0)
    resin = RESIN_PRESETS[resin_name]

    c1, c2, c3 = st.columns(3)
    with c1:
        inj_pressure = st.slider("射出圧力 [MPa]", 20, 220, 110)
        resin_temp = st.slider("樹脂温度 [℃]", 180, 350, resin["melt_temp_c"])
        mold_temp = st.slider("金型温度 [℃]", 20, 140, 60)
    with c2:
        hold_pressure = st.slider("保圧 [MPa]", 5, 160, 60)
        hold_time = st.slider("保圧時間 [s]", 0.1, 15.0, 4.0, 0.1)
        cooling_time = st.slider("冷却時間 [s]", 1.0, 40.0, 12.0, 0.5)
    with c3:
        wall_t = st.slider("代表肉厚 [mm]", 0.4, 6.0, 1.8, 0.1)
        flow_len = st.slider("代表流動長 [mm]", 10, 250, 80)
        fiber_orient = st.slider("繊維配向度 [0-1]", 0.0, 1.0, float(resin["fiber_factor"]), 0.05)

    viscosity_factor = resin["base_viscosity"] * (1.0 + (resin["melt_temp_c"] - resin_temp) / 150.0)
    flow_index = (inj_pressure / 100.0) * (resin_temp / max(1.0, resin["melt_temp_c"])) / max(0.35, viscosity_factor) * (60.0 / max(flow_len, 1.0)) * (2.2 / max(wall_t, 0.3))
    fill_pct = clamp(100.0 * logistic(flow_index, x0=0.9, k=2.5), 0, 100)

    pack_index = (hold_pressure / 60.0) * (hold_time / 4.0) * (mold_temp / 60.0)
    sink_risk = clamp(100 - 45 * pack_index - 5 * cooling_time / max(wall_t, 0.3), 0, 100)
    short_risk = clamp(100 - fill_pct, 0, 100)
    burr_risk = clamp((inj_pressure - 135) * 1.2 + (resin_temp - resin["melt_temp_c"]) * 0.25, 0, 100)

    base_shrink = resin["mold_shrink_pct"] * (1.0 + 0.10 * (resin_temp - resin["melt_temp_c"]) / 30.0)
    asymmetry = abs((mold_temp - 60) / 60.0) + 0.7 * fiber_orient + 0.15 * max(wall_t - 2.0, 0)
    warpage_index = clamp(base_shrink * asymmetry * 18.0 / max(cooling_time, 1.0), 0, 100)

    m1, m2, m3, m4, m5 = st.columns(5)
    m1.metric("充填率 [%]", f"{fill_pct:.1f}")
    m2.metric("ヒケリスク", f"{sink_risk:.1f}")
    m3.metric("ショートリスク", f"{short_risk:.1f}")
    m4.metric("バリリスク", f"{burr_risk:.1f}")
    m5.metric("反り指標", f"{warpage_index:.1f}")

    x = np.linspace(0, flow_len, 100)
    centerline = 0.2 * np.sin(2 * np.pi * x / max(flow_len, 1.0))
    warp_curve = centerline + (warpage_index / 100.0) * (x / max(flow_len, 1.0) - 0.5) ** 2 * 8 - warpage_index / 60.0
    plot_single(x, [warp_curve], ["反り模式"], "流動方向位置 [mm]", "変位指標", "成形品反りの簡易模式図")

    if show_formulas:
        st.code(
            "flow_index = (射出圧力/100) * (樹脂温度/基準溶融温度) / 粘度係数 * (60/流動長) * (2.2/肉厚)\n"
            "fill_pct = 100 * logistic(flow_index)\n"
            "sink_risk ≈ 100 - 45*pack_index - 5*冷却時間/肉厚\n"
            "warpage_index ≈ 収縮率 * 非対称係数 * 18 / 冷却時間"
        )
    if show_limits:
        st.info(
            "前提: 1点ゲート・単純流路を想定した簡易傾向モデルです。"
            " 実際にはゲート位置、金型剛性、結晶化、繊維配向テンソル、保圧切替、"
            " そり拘束条件で大きく変わります。"
        )


# =========================================================
# 2. Springback
# =========================================================
with tabs[1]:
    section_title("金属プレス: 曲げ後のスプリングバック概念")
    preset_name = st.selectbox("母材プリセット", list(METAL_PRESETS.keys()), index=0)
    mp = METAL_PRESETS[preset_name]

    c1, c2, c3 = st.columns(3)
    with c1:
        thickness = st.slider("板厚 t [mm]", 0.1, 5.0, 0.8, 0.05)
        bend_radius = st.slider("曲げ半径 R [mm]", 0.5, 30.0, 1.5, 0.1)
        bend_angle = st.slider("曲げ角度 [deg]", 15, 180, 90)
    with c2:
        young = st.slider("ヤング率 E [GPa]", 30.0, 230.0, float(mp.young_gpa), 1.0)
        yield_stress = st.slider("降伏応力 YS [MPa]", 20.0, 600.0, float(mp.yield_mpa), 1.0)
        k_factor = st.slider("加工拘束係数", 0.3, 1.5, 1.0, 0.05)
    with c3:
        friction_factor = st.slider("摩擦/拘束補正", 0.5, 1.5, 1.0, 0.05)
        hardening_factor = st.slider("加工硬化補正", 0.7, 1.3, 1.0, 0.05)
        overbend = st.slider("見込み曲げ追加 [deg]", 0.0, 15.0, 0.0, 0.1)

    # very simplified trend equation
    springback_deg = clamp(
        bend_angle * (yield_stress / (young * 1000.0)) * (bend_radius / max(thickness, 0.05)) * 18.0 / max(k_factor, 0.1) / friction_factor * hardening_factor,
        0.0, 45.0
    )
    final_angle = bend_angle + overbend - springback_deg

    neutral = thickness / 2.0
    y = np.linspace(-neutral, neutral, 200)
    strain = y / max(bend_radius + neutral, 1e-6)
    stress = np.clip(strain * young * 1000, -yield_stress, yield_stress)

    m1, m2, m3 = st.columns(3)
    m1.metric("推定スプリングバック [deg]", f"{springback_deg:.2f}")
    m2.metric("見込み曲げ後の最終角度 [deg]", f"{final_angle:.2f}")
    m3.metric("R/t", f"{bend_radius / max(thickness, 0.01):.2f}")

    plot_single(y, [stress], ["板厚方向応力"], "板厚位置 [mm]", "応力 [MPa]", "板厚方向の簡易応力分布")

    if show_formulas:
        st.code(
            "springback_deg ≈ 曲げ角度 × (YS / E) × (R/t) × 補正係数\n"
            "final_angle = 曲げ角度 + 見込み曲げ - springback_deg"
        )
    if show_limits:
        st.info(
            "前提: 単純V曲げ/曲げ戻り傾向を表す簡易式です。"
            " 実際には異方性、板取り方向、工具クリアランス、接触、Bauschinger効果、"
            " 材料モデルで変化します。"
        )


# =========================================================
# 3. Leveler concept
# =========================================================
with tabs[2]:
    section_title("レベラー概念: 複数ロール矯正の傾向把握")
    c1, c2, c3 = st.columns(3)
    with c1:
        n_roll = st.slider("有効ロール数", 3, 21, 11, 2)
        pitch = st.slider("ロールピッチ [mm]", 8.0, 40.0, 16.0, 0.5)
        roll_dia = st.slider("ロール径 [mm]", 6.0, 40.0, 12.0, 0.5)
    with c2:
        press_in = st.slider("最大押込み量 [mm]", 0.01, 3.0, 0.6, 0.01)
        strip_t = st.slider("板厚 [mm]", 0.1, 3.0, 0.8, 0.05)
        ys_lvl = st.slider("降伏応力 [MPa]", 30, 500, 110)
    with c3:
        entry_camber = st.slider("入側反り高さ(代表) [mm/400mm]", 0.0, 20.0, 3.0, 0.1)
        elastic_mod = st.slider("ヤング率 [GPa]", 30.0, 230.0, 69.0, 1.0)
        decay = st.slider("押込み減衰率", 0.70, 1.00, 0.92, 0.01)

    roll_positions = np.arange(n_roll) * pitch
    amplitudes = np.array([press_in * (decay ** i) for i in range(n_roll)])
    plasticity_index = clamp((press_in / max(strip_t, 0.05)) * (120 / max(ys_lvl, 1)) * 35, 0, 100)
    flatness_improve = clamp(20 + plasticity_index * 0.7 - entry_camber * 2.5, 0, 100)
    residual_stress_index = clamp(plasticity_index * 0.65 + (roll_dia / max(strip_t, 0.05)) * 0.15, 0, 100)

    m1, m2, m3 = st.columns(3)
    m1.metric("塑性化指標", f"{plasticity_index:.1f}")
    m2.metric("平坦度改善指標", f"{flatness_improve:.1f}")
    m3.metric("残留応力指標", f"{residual_stress_index:.1f}")

    xx = np.linspace(0, pitch * max(n_roll - 1, 1), 400)
    yy = np.zeros_like(xx)
    for pos, amp in zip(roll_positions, amplitudes):
        yy += amp * np.exp(-((xx - pos) / max(roll_dia, 1.0)) ** 2) * ((-1) ** int(pos / pitch))
    yy += entry_camber * ((xx / max(xx.max(), 1)) - 0.5) ** 2 / 10.0

    plot_single(xx, [yy], ["通板時の簡易曲げ状態"], "位置 [mm]", "たわみ指標", "レベラー通過時の模式")

    if show_formulas:
        st.code(
            "plasticity_index ≈ (押込み/板厚) × (120/YS) × 35\n"
            "flatness_improve ≈ 20 + 0.7×plasticity_index - 2.5×入側反り\n"
            "residual_stress_index ≈ 0.65×plasticity_index + 0.15×(ロール径/板厚)"
        )
    if show_limits:
        st.info(
            "前提: 11ロール前後の多点曲げを概念化したモデルです。"
            " 実際の残留応力低減や曲率履歴は接触、摩擦、板取り方向、"
            " 材料履歴、送り張力で大きく変わります。"
        )


# =========================================================
# 4. Reflow
# =========================================================
with tabs[3]:
    section_title("母材＋めっき＋リフロー: 温度プロファイルと応力・濡れ性")
    substrate_name = st.selectbox("母材", list(METAL_PRESETS.keys()), index=2)
    plate_name = st.selectbox("表層めっき", ["Sn"], index=0)
    sub = METAL_PRESETS[substrate_name]
    plate = PLATING_PRESETS[plate_name]

    c1, c2, c3 = st.columns(3)
    with c1:
        peak_temp = st.slider("ピーク温度 [℃]", 180, 320, 245)
        time_above_liquidus = st.slider("液相線超え時間 [s]", 0, 180, 45)
        ramp_rate = st.slider("昇温速度 [℃/s]", 0.5, 5.0, 1.5, 0.1)
    with c2:
        substrate_t = st.slider("母材厚み [mm]", 0.05, 2.0, 0.8, 0.01)
        plate_t = st.slider("Sn厚み [μm]", 0.1, 20.0, 3.0, 0.1)
        ni_barrier = st.slider("Niバリア厚み [μm] (参考)", 0.0, 5.0, 0.0, 0.1)
    with c3:
        initial_temp = st.slider("開始温度 [℃]", 20, 180, 25)
        cooling_rate = st.slider("冷却速度 [℃/s]", 0.5, 6.0, 2.0, 0.1)
        oxidation_penalty = st.slider("酸化/濡れ阻害補正", 0.5, 1.5, 1.0, 0.05)

    total_heat_time = (peak_temp - initial_temp) / ramp_rate + time_above_liquidus + max(peak_temp - 100, 1) / cooling_rate
    t = np.linspace(0, total_heat_time, 500)
    T = np.piecewise(
        t,
        [
            t <= (peak_temp - initial_temp) / ramp_rate,
            (t > (peak_temp - initial_temp) / ramp_rate) & (t <= (peak_temp - initial_temp) / ramp_rate + time_above_liquidus),
            t > (peak_temp - initial_temp) / ramp_rate + time_above_liquidus,
        ],
        [
            lambda tt: initial_temp + ramp_rate * tt,
            lambda tt: peak_temp,
            lambda tt: peak_temp - cooling_rate * (tt - ((peak_temp - initial_temp) / ramp_rate + time_above_liquidus)),
        ],
    )
    T = np.clip(T, 20, peak_temp)

    liquid_fraction = np.clip((T - plate["melt_c"]) / max(peak_temp - plate["melt_c"], 1e-6), 0, 1)
    wetting_index = clamp((liquid_fraction.mean() * 100) + 0.6 * time_above_liquidus - 20 * (oxidation_penalty - 1.0) - 8 * max(plate_t - 5, 0), 0, 100)

    delta_alpha = abs(sub.thermal_expansion_ppm - plate["cte_ppm"]) * 1e-6
    delta_t = max(peak_temp - initial_temp, 1.0)
    interface_stress_mpa = (min(sub.young_gpa, plate["young_gpa"]) * 1000) * delta_alpha * delta_t / max(1 + substrate_t / 0.3, 1.0)
    peel_risk = clamp(interface_stress_mpa * 0.35 + 20 * (oxidation_penalty - 1.0), 0, 100)

    m1, m2, m3 = st.columns(3)
    m1.metric("濡れ性指標", f"{wetting_index:.1f}")
    m2.metric("界面応力目安 [MPa]", f"{interface_stress_mpa:.1f}")
    m3.metric("剥離/界面リスク", f"{peel_risk:.1f}")

    plot_single(t, [T], ["炉内温度"], "時間 [s]", "温度 [℃]", "リフロー温度プロファイル")
    plot_single(t, [liquid_fraction], ["液相率"], "時間 [s]", "液相率 [-]", "Sn層の簡易液相率")

    if show_formulas:
        st.code(
            "界面応力目安 ≈ min(E_sub, E_plate) × |α_sub - α_plate| × ΔT / 厚み補正\n"
            "濡れ性指標 ≈ 平均液相率×100 + 0.6×液相線超え時間 - 酸化補正"
        )
    if show_limits:
        st.info(
            "前提: 炉内雰囲気、フラックス、表面粗さ、界面酸化膜、"
            " 実際のぬれ拡がり形状は簡略化しています。"
        )


# =========================================================
# 5. Ni strike comparison
# =========================================================
with tabs[4]:
    section_title("Niストライク有無比較: 界面拡散・濡れ性・ボイド傾向")
    c1, c2, c3 = st.columns(3)
    with c1:
        comp_temp = st.slider("比較温度 [℃]", 180, 320, 245)
        comp_time = st.slider("保持時間 [s]", 0, 180, 40)
    with c2:
        sn_thick = st.slider("Sn厚み [μm]", 0.2, 20.0, 3.0, 0.1)
        ni_thick = st.slider("Niストライク厚み [μm]", 0.05, 2.0, 0.3, 0.05)
    with c3:
        surface_clean = st.slider("表面清浄度", 0.5, 1.5, 1.0, 0.05)
        base_cu_exposure = st.slider("Cu露出傾向", 0.5, 1.5, 1.0, 0.05)

    no_ni_diffusion = clamp((comp_temp - 180) * 0.35 + comp_time * 0.28 + 8 * base_cu_exposure, 0, 100)
    with_ni_diffusion = clamp(no_ni_diffusion * max(0.15, 1 - 0.55 * ni_thick), 0, 100)

    no_ni_wetting = clamp(55 + 0.18 * comp_time + 0.25 * (comp_temp - 200) + 10 * surface_clean, 0, 100)
    with_ni_wetting = clamp(no_ni_wetting - 4 + 6 * surface_clean, 0, 100)

    no_ni_void = clamp(no_ni_diffusion * 0.42 + max(sn_thick - 5, 0) * 5, 0, 100)
    with_ni_void = clamp(no_ni_void * max(0.3, 1 - 0.35 * ni_thick), 0, 100)

    df_comp = pd.DataFrame({
        "項目": ["界面拡散指標", "濡れ性指標", "ボイド傾向"],
        "Niなし": [no_ni_diffusion, no_ni_wetting, no_ni_void],
        "Niあり": [with_ni_diffusion, with_ni_wetting, with_ni_void],
    })
    st.dataframe(df_comp, use_container_width=True)

    x = np.arange(len(df_comp))
    fig, ax = plt.subplots(figsize=(8, 4.2))
    width = 0.35
    ax.bar(x - width/2, df_comp["Niなし"], width=width, label="Niなし")
    ax.bar(x + width/2, df_comp["Niあり"], width=width, label="Niあり")
    ax.set_xticks(x)
    ax.set_xticklabels(df_comp["項目"])
    ax.set_ylabel("指標")
    ax.set_title("Niストライク有無の比較")
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend()
    st.pyplot(fig)

    if show_formulas:
        st.code(
            "Niなし拡散指標 ≈ 温度寄与 + 時間寄与 + Cu露出傾向\n"
            "Niあり拡散指標 ≈ Niなし拡散指標 × (1 - 0.55×Ni厚み)\n"
            "ボイド傾向 ≈ 拡散指標の関数 + 厚み過多補正"
        )
    if show_limits:
        st.info(
            "前提: Niストライクは界面拡散を抑える方向で簡略化しています。"
            " 実際には浴組成、下地状態、めっき結晶性、リフロー回数、"
            " 保管酸化でも結果が変わります。"
        )


# =========================================================
# 6. IMC growth
# =========================================================
with tabs[5]:
    section_title("IMC成長: Cu6Sn5 / Cu3Sn の簡易成長")
    c1, c2, c3 = st.columns(3)
    with c1:
        imc_temp = st.slider("温度 [℃]", 80, 320, 245)
        imc_time = st.slider("保持時間 [s]", 1, 3600, 60)
    with c2:
        sn_um = st.slider("Sn厚み [μm]", 0.2, 20.0, 3.0, 0.1)
        ni_um = st.slider("Niバリア厚み [μm]", 0.0, 5.0, 0.3, 0.1)
    with c3:
        cycles = st.slider("リフロー回数", 1, 10, 1)
        accel = st.slider("成長加速係数", 0.5, 2.0, 1.0, 0.05)

    sec = np.linspace(1, imc_time, 300)
    # Simplified parabolic growth with Arrhenius-like temp factor
    temp_factor = math.exp((imc_temp - 180) / 85.0)
    barrier_factor = max(0.15, 1.0 - 0.22 * ni_um)
    cu6sn5 = accel * 0.010 * temp_factor * np.sqrt(sec) * cycles * barrier_factor
    cu3sn = accel * 0.0035 * max(0.7, temp_factor - 0.2) * np.sqrt(sec) * cycles * barrier_factor
    total_imc = cu6sn5 + cu3sn
    total_imc = np.minimum(total_imc, sn_um * 1.2)

    risk_brittle = clamp(float(total_imc[-1] * 12 + cu3sn[-1] * 18), 0, 100)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Cu6Sn5終点 [μm]", f"{cu6sn5[-1]:.3f}")
    m2.metric("Cu3Sn終点 [μm]", f"{cu3sn[-1]:.3f}")
    m3.metric("総IMC終点 [μm]", f"{total_imc[-1]:.3f}")
    m4.metric("脆化リスク指標", f"{risk_brittle:.1f}")

    plot_single(sec, [cu6sn5, cu3sn, total_imc], ["Cu6Sn5", "Cu3Sn", "Total IMC"], "時間 [s]", "厚み [μm]", "IMC成長の簡易モデル")

    if show_formulas:
        st.code(
            "IMC厚み ≈ k(T) × sqrt(t) × 回数補正 × Niバリア補正\n"
            "k(T) は簡略 Arrhenius 風の温度依存\n"
            "総IMC = Cu6Sn5 + Cu3Sn"
        )
    if show_limits:
        st.info(
            "前提: 放物成長則の簡略化です。"
            " 実際には界面粗さ、空孔、応力、粒成長、局所組成、"
            " 複数回熱履歴の非線形性を含みます。"
        )


# =========================================================
# 7. CSV overlay
# =========================================================
with tabs[6]:
    section_title("CSV実測重ね表示")
    st.write("テンプレートCSVに近い形式でアップロードすると、実測との比較に使えます。")
    uploaded = st.file_uploader("CSVまたはExcelをアップロード", type=["csv", "xlsx", "xls"])

    if uploaded is not None:
        df = load_csv(uploaded)
        st.dataframe(df.head(20), use_container_width=True)

        cols = list(df.columns)
        if len(cols) >= 2:
            x_col = st.selectbox("X軸列", cols, index=0)
            y_cols = st.multiselect("Y軸列", cols, default=cols[1:min(4, len(cols))])
            if y_cols:
                overlay_csv_plot(df, x_col, y_cols, "実測重ね表示", x_col, "値",)
        else:
            st.warning("少なくとも2列以上のデータが必要です。")

    st.markdown("#### 推奨テンプレート例")
    st.code(
        "time_s,temp_c,liquid_fraction_measured,wetting_score\n"
        "0,25,0,0\n"
        "10,100,0,5\n"
        "20,180,0,15\n"
        "40,245,0.9,80\n"
        "70,220,0.3,65"
    )


# =========================================================
# 8. Protocol
# =========================================================
with tabs[7]:
    section_title("Claude / Codex に渡すための前提")
    st.markdown("""
- このアプリは**教育・仮説整理・会議説明用**の簡易シミュレータです。
- 目的は、射出成形、金属プレスのスプリングバック、レベラー概念、母材＋めっき＋リフロー、Niストライク比較、IMC成長を**1つのUIに集約**することです。
- 今後の高度化候補:
  1. 材料DBの外部CSV化
  2. 実測CSVとの自動フィッティング
  3. 炉プロファイルの多ゾーン化
  4. レベラーの応力履歴近似の強化
  5. Ni/Sn/Cu 系のより現実的な反応速度式
  6. 顧客提出用モードと教育用モードの分離
- 重要: 簡易式の係数は現場の実測で再同定してください。
    """)
    if language == "English keywords mixed":
        st.markdown("""
**Keyword map:** Injection molding / Sink mark / Short shot / Burr / Warpage / Springback / Leveler /
Reflow / Wetting / Interface stress / Ni strike / IMC growth / Cu6Sn5 / Cu3Sn
        """)
