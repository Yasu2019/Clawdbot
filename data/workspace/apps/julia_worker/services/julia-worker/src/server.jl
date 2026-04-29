module ClawstackJuliaNumericalWorker

using HTTP
using JSON3
using Random
using Statistics
using LinearAlgebra

const VERSION = "2026.04.29-regenerated"

function json_response(obj; status=200)
    return HTTP.Response(status, ["Content-Type" => "application/json; charset=utf-8"], JSON3.write(obj))
end

function read_json(req)
    body = String(req.body)
    if isempty(strip(body))
        return Dict{String,Any}()
    end
    return JSON3.read(body, Dict{String,Any})
end

function getnum(d, key::String, default::Real)
    if haskey(d, key)
        return Float64(d[key])
    else
        return Float64(default)
    end
end

function getint(d, key::String, default::Integer)
    if haskey(d, key)
        return Int(d[key])
    else
        return Int(default)
    end
end

"""
簡易レベラー推定モデル。
注意:
  これは現場検討用の近似であり、正式なCAE結果ではない。
  レベラー条件の相対比較・探索用の軽量モデルとして使う。
"""
function estimate_leveler(input::Dict{String,Any})
    t = getnum(input, "thickness_mm", 0.8)
    ys = getnum(input, "yield_mpa", 85.0)
    dia = getnum(input, "roller_diameter_mm", 12.0)
    pitch = getnum(input, "pitch_mm", 16.0)
    entry_gap = getnum(input, "entry_gap_mm", 0.7)
    exit_gap = getnum(input, "exit_gap_mm", 1.1)
    stages = getint(input, "stages", 11)
    friction = getnum(input, "friction", 0.05)

    entry_reduction = max(0.0, (t - entry_gap) / max(t, 1e-6))
    exit_reduction = max(0.0, (t - exit_gap) / max(t, 1e-6))
    staged_decay = max(0.05, 1.0 - (exit_gap - entry_gap) / max(2.5*t, 1e-6))

    curvature_input = entry_reduction * (dia / max(pitch, 1e-6)) * staged_decay
    plasticity_index = curvature_input * ys / 100.0 * sqrt(max(stages, 1))
    residual_curvature_score = abs(exit_reduction - 0.35*entry_reduction) + 0.08*friction
    springback_risk = 1.0 / (1.0 + plasticity_index)
    mesh_divergence_risk = clamp(2.8*entry_reduction + 0.8*friction - 0.15, 0.0, 1.0)

    recommended = residual_curvature_score < 0.18 && mesh_divergence_risk < 0.65

    return Dict(
        "version" => VERSION,
        "model_type" => "relative_screening_model_not_final_cae",
        "input" => input,
        "outputs" => Dict(
            "entry_reduction_ratio" => entry_reduction,
            "exit_reduction_ratio" => exit_reduction,
            "plasticity_index" => plasticity_index,
            "residual_curvature_score" => residual_curvature_score,
            "springback_risk_score" => springback_risk,
            "mesh_divergence_risk_score" => mesh_divergence_risk,
            "recommended_for_next_cae" => recommended
        ),
        "notes" => [
            "この結果は相対比較用です。",
            "正式評価はPrePoMax/CalculiX/Elmer/OpenFOAM等のCAE結果で確認してください。",
            "入口側を強め、出口側を弱める条件探索の初期スクリーニングに使います。"
        ]
    )
end

function latin_hypercube(input::Dict{String,Any})
    n = getint(input, "n", 10)
    seed = getint(input, "seed", 42)
    vars = input["variables"]
    rng = MersenneTwister(seed)
    rows = Vector{Dict{String,Float64}}()

    names = collect(keys(vars))
    columns = Dict{String,Vector{Float64}}()

    for name in names
        lo = Float64(vars[name][1])
        hi = Float64(vars[name][2])
        bins = ((0:n-1) .+ rand(rng, n)) ./ n
        shuffle!(rng, bins)
        columns[String(name)] = lo .+ bins .* (hi - lo)
    end

    for i in 1:n
        row = Dict{String,Float64}()
        for name in names
            row[String(name)] = columns[String(name)][i]
        end
        push!(rows, row)
    end

    return Dict(
        "version" => VERSION,
        "method" => "latin_hypercube_simple",
        "n" => n,
        "rows" => rows
    )
end

function range_values(spec)
    start = Float64(spec[1])
    stop = Float64(spec[2])
    step = Float64(spec[3])
    vals = Float64[]
    x = start
    while x <= stop + 1e-9
        push!(vals, round(x, digits=6))
        x += step
    end
    return vals
end

function optimize_leveler_grid(input::Dict{String,Any})
    entry_vals = range_values(input["entry_gap_range"])
    exit_vals = range_values(input["exit_gap_range"])

    best = nothing
    results = Vector{Dict{String,Any}}()

    for eg in entry_vals
        for xg in exit_vals
            trial = copy(input)
            trial["entry_gap_mm"] = eg
            trial["exit_gap_mm"] = xg
            est = estimate_leveler(trial)
            score = est["outputs"]["residual_curvature_score"] +
                    0.30 * est["outputs"]["springback_risk_score"] +
                    0.50 * est["outputs"]["mesh_divergence_risk_score"]
            row = Dict(
                "entry_gap_mm" => eg,
                "exit_gap_mm" => xg,
                "objective_score" => score,
                "estimate" => est["outputs"]
            )
            push!(results, row)
            if best === nothing || score < best["objective_score"]
                best = row
            end
        end
    end

    sort!(results, by = x -> x["objective_score"])

    return Dict(
        "version" => VERSION,
        "method" => "grid_search_relative_screening",
        "best" => best,
        "top10" => results[1:min(10, length(results))],
        "count" => length(results),
        "warning" => "簡易相対モデルです。正式なCAEや実測で必ず確認してください。"
    )
end

function handle(req::HTTP.Request)
    try
        method = String(req.method)
        path = String(HTTP.URI(req.target).path)

        if method == "GET" && path == "/health"
            return json_response(Dict(
                "ok" => true,
                "service" => "clawstack-julia-numerical-worker",
                "version" => VERSION,
                "julia_version" => string(VERSION),
                "threads" => Threads.nthreads()
            ))
        elseif method == "POST" && path == "/leveler/estimate"
            return json_response(estimate_leveler(read_json(req)))
        elseif method == "POST" && path == "/doe/latin_hypercube"
            return json_response(latin_hypercube(read_json(req)))
        elseif method == "POST" && path == "/optimize/leveler_grid"
            return json_response(optimize_leveler_grid(read_json(req)))
        else
            return json_response(Dict("ok" => false, "error" => "not_found", "path" => path), status=404)
        end
    catch err
        return json_response(Dict(
            "ok" => false,
            "error" => string(err),
            "type" => string(typeof(err))
        ), status=500)
    end
end

function main()
    host = get(ENV, "JULIA_WORKER_HOST", "0.0.0.0")
    port = parse(Int, get(ENV, "JULIA_WORKER_PORT", "8096"))
    println("Starting Clawstack Julia Numerical Worker on $(host):$(port)")
    HTTP.serve(handle, host, port)
end

end # module

ClawstackJuliaNumericalWorker.main()
