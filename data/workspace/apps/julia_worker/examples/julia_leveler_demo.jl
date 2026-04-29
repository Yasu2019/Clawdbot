# Julia単体での簡易デモ用
# 実際のWorkerとは別に、考え方を確認するための簡易スクリプトです。

function estimate_leveler(; thickness_mm=0.8, yield_mpa=85, roller_diameter_mm=12,
    pitch_mm=16, entry_gap_mm=0.7, exit_gap_mm=1.1, stages=11, friction=0.05)

    entry_reduction = max(0.0, (thickness_mm - entry_gap_mm) / thickness_mm)
    exit_reduction = max(0.0, (thickness_mm - exit_gap_mm) / thickness_mm)
    staged_decay = max(0.05, 1.0 - (exit_gap_mm - entry_gap_mm) / (2.5thickness_mm))

    curvature_input = entry_reduction * (roller_diameter_mm / pitch_mm) * staged_decay
    plasticity_index = curvature_input * yield_mpa / 100.0 * sqrt(stages)
    residual_curvature_score = abs(exit_reduction - 0.35entry_reduction) + 0.08friction
    springback_risk = 1.0 / (1.0 + plasticity_index)

    return (; entry_reduction, exit_reduction, plasticity_index, residual_curvature_score, springback_risk)
end

println(estimate_leveler())
