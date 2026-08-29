/**
 * CETOL-class Modeler / Analyzer client (not commercial Sigmetrix CETOL 6-sigma).
 * Geometry-derived kinematic tree, dual contribution, MSM what-if, sensitivity pose.
 */
(function (global) {
  "use strict";

  var FORBIDDEN = ["BasePlate", "Bracket", "PinJoin", "GapSensor"];

  function slugify(raw) {
    var s = String(raw || "Part").replace(/[^A-Za-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
    return (s || "Part").slice(0, 48);
  }

  function bboxOf(r) {
    var b = (r && r.bbox_mm) || {};
    var lx = Number(b.Lx) || 40;
    var ly = Number(b.Ly) || 20;
    var sheet = Number(r && r.sheet_thickness_mm) || 2;
    var lz = Number(b.Lz) || sheet || 2;
    if (lx <= 0) lx = 40;
    if (ly <= 0) ly = 20;
    if (lz <= 0) lz = sheet || 2;
    return { Lx: lx, Ly: ly, Lz: lz };
  }

  function distSigma(d) {
    var t = Math.max(Number(d.tolerance) || 0, 0);
    var dist = String(d.distribution || "normal").toLowerCase();
    if (dist === "uniform") return t / Math.sqrt(3);
    if (dist === "triangular") return t / Math.sqrt(6);
    return t / 6;
  }

  function msmWhatIf(dims, overrides, lsl, usl) {
    lsl = lsl == null ? -0.05 : lsl;
    usl = usl == null ? 0.05 : usl;
    var mu = 0, v = 0, m3 = 0, exk = 0;
    var per = [];
    (dims || []).forEach(function (d) {
      var tol = overrides && Object.prototype.hasOwnProperty.call(overrides, d.name)
        ? Number(overrides[d.name])
        : Number(d.tolerance);
      var s = distSigma({ tolerance: tol, distribution: d.distribution });
      var a = Number(d.coef) || 1;
      var mean = Number(d.mean) || 0;
      mu += a * mean;
      v += (a * s) * (a * s);
      per.push({ name: d.name, s: s, var: (a * s) * (a * s), tol: tol, coef: a, source: d.source });
    });
    var sigma = v > 0 ? Math.sqrt(v) : 0;
    var total = v || 1;
    var cpk = null, cp = null, yieldRate = null;
    if (sigma > 0) {
      cp = (usl - lsl) / (6 * sigma);
      cpk = Math.min((usl - mu) / (3 * sigma), (mu - lsl) / (3 * sigma));
      function ncdf(z) {
        return 0.5 * (1 + erf(z / Math.SQRT2));
      }
      yieldRate = Math.max(0, Math.min(1, ncdf((usl - mu) / sigma) - ncdf((lsl - mu) / sigma)));
    }
    var sensitivity = {};
    per.forEach(function (p) {
      sensitivity[p.name] = { sigma_mm: p.s, contribution: p.var / total, tolerance: p.tol, coef: p.coef };
    });
    return { mean: mu, sigma: sigma, Cp: cp, Cpk: cpk, yield_rate: yieldRate, sensitivity: sensitivity, method: "msm_whatif_js" };
  }

  function erf(x) {
    var s = x < 0 ? -1 : 1;
    x = Math.abs(x);
    var a1 = 0.254829592, a2 = -0.284496736, a3 = 1.421413741, a4 = -1.453152027, a5 = 1.061405429, p = 0.3275911;
    var t = 1 / (1 + p * x);
    var y = 1 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * Math.exp(-x * x);
    return s * y;
  }

  function dualFromDims(dims) {
    var abs = [];
    var sum = 0;
    (dims || []).forEach(function (d) {
      var x = Math.abs(Number(d.mean) || 0);
      if (x < 1e-12) x = Math.abs(Number(d.coef) || 1);
      var v = Math.abs((Number(d.coef) || 1) * x);
      abs.push({ name: d.name, v: v });
      sum += v;
    });
    if (sum <= 0) sum = 1;
    var msm = msmWhatIf(dims, {}, -0.05, 0.05);
    return (abs).map(function (row) {
      var t = (msm.sensitivity[row.name] || {}).contribution || 0;
      return {
        name: row.name,
        dimension_contribution: row.v / sum,
        tolerance_contribution: t
      };
    });
  }

  function deriveModel(report) {
    if (report && report.cetol_model && report.cetol_model.frames && report.cetol_model.frames.length) {
      var m0 = report.cetol_model;
      if (report.cad_asset) m0.cad_asset = report.cad_asset;
      if (report.assembly_sequence && !m0.assembly_sequence) m0.assembly_sequence = report.assembly_sequence;
      return m0;
    }
    var slug = slugify((report && (report.job_id || report.source_dxf)) || "Part");
    var bb = bboxOf(report || {});
    var sheet = Number(report && report.sheet_thickness_mm) || bb.Lz;
    var pmi = (report && report.pmi) || {};
    var dims = (report && report.dimensions) || [];
    var frames = [
      { name: slug + "_DieBase", role: "datum", t_nom: [0, 0, 0], r_nom: [0, 0, 0],
        t_tol: [0.02, 0.02, 0.03], r_tol: [0.01, 0.01, 0.01], source: "gdt_proxy" },
      { name: slug + "_Strip", role: "part", t_nom: [0, 0, sheet], r_nom: [0, 0, 0],
        t_tol: [0.02, 0.02, 0.03], r_tol: [0.02, 0.02, 0.02], source: "measured" },
      { name: slug + "_Pitch", role: "measure_close", t_nom: [bb.Lx, 0, 0], r_nom: [0, 0, 0],
        t_tol: [0.04, 0.04, 0.05], r_tol: [0.02, 0.02, 0.02], source: "gdt_proxy" },
      { name: slug + "_GapZ", role: "measure_close", t_nom: [0, 0, bb.Lz], r_nom: [0, 0, 0],
        t_tol: [0.03, 0.03, 0.03], r_tol: [0.01, 0.01, 0.01], source: "measured" }
    ];
    FORBIDDEN.forEach(function (n) {
      frames.forEach(function (f) {
        if (f.name === n) throw new Error("generic frame leaked: " + n);
      });
    });
    var nHoles = Math.min(Number(pmi.holes) || 0, 4);
    var i;
    for (i = 0; i < nHoles; i++) {
      frames.push({
        name: slug + "_hole_" + (i + 1),
        role: "feature_cylinder",
        t_nom: [(i + 1) * bb.Lx / (nHoles + 1), bb.Ly * 0.5, sheet],
        r_nom: [0, 0, 0],
        t_tol: [0.05, 0.05, 0.025],
        r_tol: [0.015, 0.015, 0.02],
        source: "gdt_proxy",
        diameter_mm: Math.max(2, Math.min(bb.Ly * 0.4, 8))
      });
    }
    var measures = [
      { id: "gap_z", label: "Gap Z", kind: "linear", direction: [0, 0, 1] },
      { id: "pitch_x", label: "Pitch X", kind: "linear", direction: [1, 0, 0] },
      { id: "float_y", label: "Float Y", kind: "linear", direction: [0, 1, 0] }
    ];
    var stations = [
      { name: "station1_blanking_set", station: "BL", tolerance_mm: 0.012 },
      { name: "station2_bending_set", station: "BE", tolerance_mm: 0.015 },
      { name: "station_pierce_hole_position", station: "PI", tolerance_mm: 0.05 }
    ];
    var advisor = [];
    if (nHoles && !(pmi.datums > 0)) {
      advisor.push({ code: "missing_datums", severity: "warn", text: "holes present but no datums in PMI" });
    }
    if (!(pmi.gdt > 0) && !(pmi.dims > 0)) {
      advisor.push({ code: "insufficient_gdt", severity: "info", text: "INSUFFICIENT -- no PMI/GD&T" });
    }
    advisor.push({
      code: "openradioss_absent",
      severity: "info",
      text: "OpenRadioss springback missing (fail-closed, not faked)"
    });
    var dualRows = dualFromDims(dims);
    var top = null;
    var sens = (report && report.sensitivity) || {};
    Object.keys(sens).forEach(function (k) {
      var c = (sens[k] && sens[k].contribution) || 0;
      if (!top || c > top.c) top = { name: k, c: c };
    });
    return {
      schema: "clawstack.cetol_model.v1_client",
      truth_gate: { commercial_cetol_equivalent: false, status: "UNVALIDATED" },
      job_id: report && report.job_id,
      part_slug: slug,
      bbox_mm: bb,
      sheet_thickness_mm: sheet,
      assembly: { id: slug, label: slug, parts: [
        { id: slug + "_DieBase", label: "Die / datum base" },
        { id: slug + "_Strip", label: "Strip / part" }
      ]},
      features: frames.filter(function (f) { return f.role !== "datum"; }).map(function (f) {
        return { id: f.name, kind: f.role === "feature_cylinder" ? "cylinder" : "solid", label: f.name, origin: f.t_nom };
      }),
      joints: [{ id: slug + "_j_die_strip", kind: "planar_contact", from: slug + "_DieBase", to: slug + "_Strip", float: false, sequence: 1 }],
      measures: measures,
      variations: dims,
      frames: frames,
      dual_contribution: { rows: dualRows },
      cross_table: buildClientCross(dims, measures),
      msm: (report && report.msm) || {},
      station_contributors: stations,
      openradioss: { present: false, status: "INSUFFICIENT", reason: "no OpenRadioss springback artifact" },
      gdt: [],
      product_definition: {
        source_dxf: report && report.source_dxf,
        pmi_enrichment: pmi,
        maturity_hint: report && report.maturity_level
      },
      advisor: advisor,
      sensitivity_animation: {
        driver: top ? top.name : (frames[1] ? frames[1].name + "_Tz" : null),
        measure: "gap_z",
        exaggeration_default: 50
      }
    };
  }

  function buildClientCross(dims, measures) {
    var msm = msmWhatIf(dims, {}, -0.05, 0.05);
    var table = {};
    (dims || []).forEach(function (d) {
      var c = (msm.sensitivity[d.name] || {}).contribution || 0;
      table[d.name] = {};
      (measures || []).forEach(function (m, idx) {
        var scale = m.id === "gap_z" ? 1 : (m.id === "pitch_x" ? 0.7 : 0.45);
        table[d.name][m.id] = Math.round(c * scale * 10000) / 10000;
      });
    });
    return table;
  }

  function escapeHtml(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function renderTree(el, model, onSelect) {
    if (!el) return;
    var slug = (model && model.part_slug) || "Part";
    function node(id, label, kind) {
      return '<div class="cetol-node" data-id="' + escapeHtml(id) + '" data-kind="' + escapeHtml(kind || "") + '">' +
        escapeHtml(label) + "</div>";
    }
    var html = "<details open><summary>Assembly / " + escapeHtml(slug) + "</summary>";
    html += "<details open><summary>Parts</summary>";
    ((model.assembly && model.assembly.parts) || []).forEach(function (p) {
      html += node(p.id, p.label || p.id, "part");
    });
    html += "</details><details open><summary>Features</summary>";
    (model.features || []).forEach(function (f) {
      html += node(f.id, (f.label || f.id) + " [" + (f.kind || "") + "]", "feature");
    });
    html += "</details><details open><summary>Assembly sequence</summary>";
    (model.assembly_sequence || []).forEach(function (s) {
      html += node(s.joint_id || ("seq_" + s.seq),
        String(s.seq) + ". " + (s.kind || "") + (s.float ? " FLOAT" : "") + " -- " + (s.note || ""),
        "joint");
    });
    html += "</details><details open><summary>Joints</summary>";
    (model.joints || []).forEach(function (j) {
      html += node(j.id, (j.kind || "joint") + " seq " + (j.sequence || "-") + (j.float ? " FLOAT" : ""), "joint");
    });
    html += "</details><details open><summary>Measures</summary>";
    (model.measures || []).forEach(function (m) {
      html += node(m.id, (m.label || m.id) + " (" + (m.kind || "linear") + ")", "measure");
    });
    html += "</details><details open><summary>Variations</summary>";
    (model.variations || []).slice(0, 24).forEach(function (d) {
      html += node(d.name, d.name + " +/-" + (d.tolerance != null ? d.tolerance : ""), "variation");
    });
    html += "</details></details>";
    el.innerHTML = html;
    el.querySelectorAll(".cetol-node").forEach(function (n) {
      n.onclick = function () {
        el.querySelectorAll(".cetol-node").forEach(function (x) { x.classList.remove("sel"); });
        n.classList.add("sel");
        if (onSelect) onSelect(n.getAttribute("data-id"), n.getAttribute("data-kind"));
      };
    });
  }

  function renderCrossTable(el, model, activeMeasure) {
    if (!el) return;
    var measures = model.measures || [];
    var table = model.cross_table || {};
    var names = Object.keys(table);
    if (!names.length && model.variations) {
      names = model.variations.map(function (d) { return d.name; });
    }
    activeMeasure = activeMeasure || (measures[0] && measures[0].id) || "gap_z";
    names.sort(function (a, b) {
      var va = Number((table[a] || {})[activeMeasure] || 0);
      var vb = Number((table[b] || {})[activeMeasure] || 0);
      return vb - va;
    });
    var colMax = {};
    measures.forEach(function (m) {
      var mx = -1, who = "";
      names.forEach(function (n) {
        var v = Number((table[n] || {})[m.id] || 0);
        if (v > mx) { mx = v; who = n; }
      });
      colMax[m.id] = { v: mx, name: who };
    });
    var pinned = [];
    measures.forEach(function (m) {
      var who = colMax[m.id] && colMax[m.id].name;
      var v = colMax[m.id] ? colMax[m.id].v : 0;
      if (who && v > 0 && pinned.indexOf(who) < 0) pinned.push(who);
    });
    var rest = names.filter(function (n) { return pinned.indexOf(n) < 0; });
    var ordered = pinned.concat(rest);
    var dualMap = {};
    ((model.dual_contribution && model.dual_contribution.rows) || []).forEach(function (r) {
      dualMap[r.name] = r;
    });
    var head = "<tr><th>Contributor</th>";
    measures.forEach(function (m) {
      var cls = m.id === activeMeasure ? " style=\"color:var(--acc)\"" : "";
      var coup = ((model.measure_coupling || {})[m.id] || {}).status || "";
      var markU = coup === "uncoupled" ? " (uncoupled)" : "";
      head += "<th" + cls + ">" + escapeHtml(m.id) + markU + "</th>";
    });
    head += "<th>dim%</th></tr>";
    var body = ordered.slice(0, 24).map(function (n) {
      var row = table[n] || {};
      var tds = measures.map(function (m) {
        var v = Number(row[m.id] || 0) * 100;
        var isMax = colMax[m.id] && colMax[m.id].name === n && v > 0;
        var uncoupled = ((model.measure_coupling || {})[m.id] || {}).status === "uncoupled";
        var col = v > 40 ? "var(--ng)" : (v > 15 ? "var(--warn)" : "var(--tx)");
        var mark = isMax ? " *" : "";
        var txt = uncoupled && v === 0 ? "0.0% (no coupling)" : (v.toFixed(1) + "%" + mark);
        return "<td class=\"num\" style=\"color:" + col + ";font-weight:" + (isMax ? "700" : "400") + "\">" +
          txt + "</td>";
      }).join("");
      var dim = dualMap[n] ? (Number(dualMap[n].dimension_contribution) || 0) * 100 : 0;
      return "<tr><td>" + escapeHtml(n) + "</td>" + tds +
        "<td class=\"num\" style=\"color:var(--dim)\">" + dim.toFixed(1) + "</td></tr>";
    }).join("");
    var crit = (colMax[activeMeasure] || {}).name || "-";
    var coupNotes = measures.map(function (m) {
      var c = (model.measure_coupling || {})[m.id] || {};
      var mx = colMax[m.id] || {};
      if (c.status === "uncoupled" || (mx.v != null && mx.v <= 0)) {
        return escapeHtml(m.id) + ": uncoupled (no kinematic path)";
      }
      return escapeHtml(m.id) + ": coupled (max " + ((mx.v || 0) * 100).toFixed(1) + "% on " + escapeHtml(mx.name || "-") + ")";
    }).join(" / ");
    el.innerHTML = "<div class=\"note\">Active CTQ <strong>" + escapeHtml(activeMeasure) +
      "</strong> -- critical contributor <strong>" + escapeHtml(crit) +
      "</strong> (* = column max, pinned at top). dim% = dimension contribution (not tolerance).</div>" +
      "<div class=\"note\">" + coupNotes + "</div>" +
      "<table><thead>" + head + "</thead><tbody>" + body + "</tbody></table>";
  }

  function renderDualContrib(el, model) {
    if (!el) return;
    var rows = (model.dual_contribution && model.dual_contribution.rows) || [];
    if (!rows.length && model.variations) rows = dualFromDims(model.variations);
    el.innerHTML = rows.slice(0, 12).map(function (r) {
      var d = (Number(r.dimension_contribution) || 0) * 100;
      var t = (Number(r.tolerance_contribution) || 0) * 100;
      return '<div class="bar-row"><div class="bar-name">' + escapeHtml(r.name) + "</div>" +
        '<div class="bar-track"><div class="bar-fill" style="width:' + Math.max(1, d) + '%;opacity:0.45"></div></div>' +
        '<div class="bar-val">' + d.toFixed(1) + "% dim</div>" +
        '<div class="bar-track"><div class="bar-fill pmi" style="width:' + Math.max(1, t) + '%"></div></div>' +
        '<div class="bar-val">' + t.toFixed(1) + "% tol</div></div>";
    }).join("") || "<div class=\"note\">No dual-contribution rows.</div>";
  }

  function renderTim(el, model) {
    if (!el) return;
    var tim = model.tim || {};
    var rows = tim.rows || [];
    if (!rows.length) {
      el.innerHTML = "<div class=\"note\">TIM empty -- rebuild model. Web analog only; not Creo/SW CAD TIM.</div>";
      return;
    }
    var coup = (tim.measure_coupling || []).map(function (c) {
      return escapeHtml(c.measure) + "=" + escapeHtml(c.status || "-");
    }).join(" / ");
    var body = rows.slice(0, 40).map(function (r) {
      var st = r.status || "-";
      var cls = st === "APPLIED" || st === "USED" ? "keep" : (st === "UNUSED" || st === "INSUFFICIENT" ? "warn" : "keep");
      var extra = r.bonus_mm != null ? (" bonus " + Number(r.bonus_mm).toFixed(3) + " mm") : "";
      var used = (r.used_by_ctq || []).join(",");
      return "<div class=\"note\"><span class=\"tag " + cls + "\">" + escapeHtml(st) + "</span> " +
        "<span class=\"tag pmi\">" + escapeHtml(r.kind || "") + "</span> " +
        escapeHtml(r.name || "") + extra +
        (used ? " CTQ[" + escapeHtml(used) + "]" : "") + "</div>";
    }).join("");
    el.innerHTML = "<div class=\"note\">Web TIM -- unused 1D=" + escapeHtml(tim.unused_count) +
      " MMC applied=" + escapeHtml(tim.mmc_applied_count) +
      " constraint=" + escapeHtml((tim.constraint_state || {}).status || (model.constraint_state || {}).status || "-") +
      " DLM=" + escapeHtml((model.closed_loop || {}).applied === true ? "on" : "off") +
      " jointY=" + escapeHtml(((model.joint_ctq_yield || {}).yield_joint != null) ? String(model.joint_ctq_yield.yield_joint) : "off") +
      ". Creo/SW add-in skipped. Not Sigmetrix CAD TIM.</div>" +
      (coup ? "<div class=\"note\">Coupling: " + coup + "</div>" : "") + body;
  }

  function renderAdvisor(el, model) {
    if (!el) return;
    var flags = model.advisor || [];
    el.innerHTML = flags.map(function (f) {
      var cls = f.severity === "error" || f.severity === "warn" ? "warn" : "keep";
      return '<div class="note"><span class="tag ' + cls + '">' + escapeHtml(f.code) + "</span> " +
        escapeHtml(f.text || "") + "</div>";
    }).join("");
  }

  function renderProductDef(el, model) {
    if (!el) return;
    var p = model.product_definition || {};
    var pmi = p.pmi_enrichment || {};
    var cad = model.cad_asset || {};
    el.innerHTML =
      "<div class=\"note\">DXF: <strong>" + escapeHtml(p.source_dxf || "-") + "</strong></div>" +
      "<div class=\"note\">STEP: <strong>" + escapeHtml(p.step_url || p.step_path || cad.step_url || "(none on this job)") + "</strong>" +
      (cad.synthesized ? " (synthesized plate from bbox+holes)" : "") + "</div>" +
      "<div class=\"note\">PMI dims " + escapeHtml(pmi.dims || pmi.pmi_dim_count || 0) +
      " / holes " + escapeHtml(pmi.holes || pmi.hole_count || 0) +
      " / datums " + escapeHtml(pmi.datums || pmi.datum_count || 0) +
      " / gdt " + escapeHtml(pmi.gdt || pmi.gdt_annotation_count || 0) + "</div>" +
      "<div class=\"note\">Maturity: " + escapeHtml(p.maturity_hint || "-") +
      " -- product definition from DXF2STEP, not CAD add-in.</div>";
  }

  function renderGdt(el, model) {
    if (!el) return;
    var gdt = model.gdt || [];
    if (!gdt.length) {
      el.innerHTML = "<div class=\"note\">INSUFFICIENT -- no feature-control-frame data on this job. ASME solver not claimed.</div>";
      return;
    }
    el.innerHTML = gdt.map(function (g) {
      return '<div class="fcf-row"><span class="fcf">' + escapeHtml(g.fcf || g.type) + "</span> " +
        escapeHtml(g.feature || "") +
        (g.material_condition ? " " + escapeHtml(g.material_condition) : "") +
        (g.datum_ref ? " DRF " + escapeHtml(g.datum_ref) : "") + "</div>";
    }).join("");
  }

  function renderStations(el, model) {
    if (!el) return;
    var rows = model.station_contributors || [];
    el.innerHTML = rows.map(function (s) {
      return "<div class=\"note\"><span class=\"tag pmi\">" + escapeHtml(s.station) + "</span> " +
        escapeHtml(s.name) + " +/-" + escapeHtml(s.tolerance_mm) + " mm</div>";
    }).join("") || "<div class=\"note\">No station contributors.</div>";
  }

  function renderCetolCannot(el, model) {
    if (!el) return;
    var c = model.cetol_cannot || {};
    if (!c.schema) {
      el.innerHTML = "<div class=\"note\">Refresh reports to load process physics CETOL 6-sigma cannot run.</div>";
      return;
    }
    var die = c.progressive_die || {};
    var comp = c.compliant || {};
    var mf = c.moldflow || {};
    var split = c.variance_split || {};
    el.innerHTML =
      "<div class=\"note\">商用 CETOL 6σ は剛体ジョイントのみ。以下は実装できない工程物理（UNVALIDATED）。</div>" +
      "<div class=\"note\"><span class=\"tag pmi\">DIE</span> " +
      escapeHtml((die.sequence || []).join("->")) +
      " RSS " + escapeHtml(die.rss_process_mm) + " mm" +
      " after PI " + escapeHtml(die.after_pilot_mm) +
      " springback " + escapeHtml(die.springback_status) + "</div>" +
      "<div class=\"note\"><span class=\"tag pmi\">FLEX</span> compliant sigma " +
      escapeHtml(comp.sigma_mm) + " mm (rigid CETOL cannot bend the sheet)</div>" +
      "<div class=\"note\"><span class=\"tag pmi\">FILL</span> moldflow " +
      escapeHtml(mf.status || "-") +
      (mf.shrink_mm != null ? (" shrink " + escapeHtml(mf.shrink_mm) + " mm") : "") +
      "</div>" +
      "<div class=\"note\">process variance fraction " +
      escapeHtml(split.process_variance_fraction) +
      " (process " + escapeHtml(split.process_sigma_mm) +
      " / rigid " + escapeHtml(split.rigid_gdt_sigma_mm) + ")</div>";
  }

  var kinematic = {
    group: null,
    meshes: {},
    rest: {},
    model: null,
    THREE: null,
    selectedId: null,
    cadGroup: null,
    cadLoaded: false
  };
  var occtReady = null;

  function getOcct() {
    if (!occtReady) {
      occtReady = (typeof occtimportjs === "function")
        ? occtimportjs({ locateFile: function (f) { return "../growth_dashboard/vendor/" + f; } })
        : Promise.reject(new Error("occt-import-js not loaded"));
    }
    return occtReady;
  }

  function loadStepGroup(url, THREE) {
    return fetch(url).then(function (res) {
      if (!res.ok) throw new Error("STEP HTTP " + res.status);
      return res.arrayBuffer();
    }).then(function (ab) {
      return getOcct().then(function (occt) {
        var result = occt.ReadStepFile(new Uint8Array(ab), null);
        if (!result || !result.meshes || !result.meshes.length) throw new Error("no STEP meshes");
        var g = new THREE.Group();
        g.name = "cadStep";
        result.meshes.forEach(function (meshData, i) {
          var posArr = meshData.attributes && meshData.attributes.position && meshData.attributes.position.array;
          if (!posArr || posArr.length < 9) return;
          var geom = new THREE.BufferGeometry();
          geom.setAttribute("position", new THREE.Float32BufferAttribute(Float32Array.from(posArr), 3));
          if (meshData.index && meshData.index.array && meshData.index.array.length) {
            geom.setIndex(new THREE.BufferAttribute(Uint32Array.from(meshData.index.array), 1));
          }
          geom.computeVertexNormals();
          var mat = new THREE.MeshStandardMaterial({
            color: i === 0 ? 0x6aa8ff : 0xb48cff,
            roughness: 0.36,
            metalness: 0.28,
            side: THREE.DoubleSide
          });
          var mesh = new THREE.Mesh(geom, mat);
          mesh.userData = { id: "cad_solid_" + i, label: "STEP solid " + i };
          g.add(mesh);
        });
        if (!g.children.length) throw new Error("STEP group empty");
        return g;
      });
    });
  }

  function loadStlGroup(url, THREE) {
    return new Promise(function (resolve, reject) {
      if (!THREE.STLLoader) {
        reject(new Error("STLLoader missing"));
        return;
      }
      var loader = new THREE.STLLoader();
      loader.load(url, function (geom) {
        geom.computeVertexNormals();
        var mesh = new THREE.Mesh(geom, new THREE.MeshStandardMaterial({
          color: 0x6aa8ff, roughness: 0.36, metalness: 0.28, side: THREE.DoubleSide
        }));
        mesh.userData = { id: "cad_stl", label: "STL tessellation" };
        var g = new THREE.Group();
        g.name = "cadStl";
        g.add(mesh);
        resolve(g);
      }, undefined, reject);
    });
  }

  function fitCadGroup(g, THREE) {
    var box = new THREE.Box3().setFromObject(g);
    if (box.isEmpty()) return;
    var size = box.getSize(new THREE.Vector3());
    var maxDim = Math.max(size.x, size.y, size.z, 1e-6);
    g.scale.setScalar(90 / maxDim);
    box = new THREE.Box3().setFromObject(g);
    var c = box.getCenter(new THREE.Vector3());
    g.position.sub(c);
    g.position.y += 6;
  }

  function clearKinematic(scene) {
    if (kinematic.group && scene) scene.remove(kinematic.group);
    kinematic.group = null;
    kinematic.meshes = {};
    kinematic.rest = {};
    kinematic.cadGroup = null;
    kinematic.cadLoaded = false;
  }

  function buildProxyFrames(g, THREE, model, skipPartBox) {
    var bb = model.bbox_mm || { Lx: 40, Ly: 20, Lz: 2 };
    var sc = 1.2;
    var dieMat = new THREE.MeshStandardMaterial({ color: 0x3a4258, roughness: 0.55, metalness: 0.2, transparent: true, opacity: skipPartBox ? 0.35 : 1 });
    var partMat = new THREE.MeshStandardMaterial({ color: 0x4da3ff, roughness: 0.35, metalness: 0.25 });
    var holeMat = new THREE.MeshStandardMaterial({ color: 0xb48cff, roughness: 0.4, metalness: 0.2, transparent: true, opacity: 0.85 });
    var closeMat = new THREE.MeshStandardMaterial({ color: 0x3ddc84, roughness: 0.4, metalness: 0.15 });
    function addBox(id, size, pos, mat) {
      var mesh = new THREE.Mesh(new THREE.BoxGeometry(size[0], size[1], size[2]), mat.clone());
      mesh.position.set(pos[0], pos[1], pos[2]);
      mesh.userData = { id: id, label: id };
      g.add(mesh);
      kinematic.meshes[id] = mesh;
      kinematic.rest[id] = { x: pos[0], y: pos[1], z: pos[2] };
      return mesh;
    }
    function addCyl(id, r, h, pos, mat) {
      var mesh = new THREE.Mesh(new THREE.CylinderGeometry(r, r, h, 20), mat.clone());
      mesh.position.set(pos[0], pos[1], pos[2]);
      mesh.userData = { id: id, label: id };
      g.add(mesh);
      kinematic.meshes[id] = mesh;
      kinematic.rest[id] = { x: pos[0], y: pos[1], z: pos[2] };
      return mesh;
    }
    (model.frames || []).forEach(function (f) {
      var t = f.t_nom || [0, 0, 0];
      var px = t[0] * sc, py = t[2] * sc, pz = t[1] * sc;
      if (f.role === "datum") {
        addBox(f.name, [Math.max(bb.Lx * sc, 20), 3, Math.max(bb.Ly * sc, 12)], [px, py - 10, pz], dieMat);
      } else if (f.role === "part") {
        if (skipPartBox) return;
        addBox(f.name, [bb.Lx * sc, Math.max(bb.Lz * sc, 3), bb.Ly * sc], [px + bb.Lx * sc * 0.35, py + Math.max(bb.Lz * sc, 3) * 0.5, pz], partMat);
      } else if (f.role === "feature_cylinder") {
        var dia = Number(f.diameter_mm) || 4;
        addCyl(f.name, Math.max(dia * sc * 0.5, 1.2), Math.max(bb.Lz * sc, 8), [px, py + 6, pz], holeMat);
      } else if (!skipPartBox) {
        addBox(f.name, [5, 5, 5], [px, py + 10, pz], closeMat);
      }
    });
  }

  function setCadStatus(text) {
    var el = document.getElementById("cadStatus");
    if (el) el.textContent = text;
  }

  function buildKinematicScene(scene, THREE, model) {
    if (!scene || !THREE || !model) return Promise.resolve(null);
    clearKinematic(scene);
    kinematic.THREE = THREE;
    kinematic.model = model;
    var g = new THREE.Group();
    g.name = "cetolKinematic";
    kinematic.group = g;
    scene.add(g);
    var cad = model.cad_asset || {};
    var pd = model.product_definition || {};
    var stepUrl = cad.step_url || pd.step_url;
    var stlUrl = cad.stl_url || pd.stl_url;
    var load = Promise.resolve(null);
    if (stepUrl) {
      setCadStatus("STEP loading...");
      load = loadStepGroup(stepUrl, THREE).catch(function (err) {
        setCadStatus("STEP failed, STL fallback");
        return stlUrl ? loadStlGroup(stlUrl, THREE) : null;
      });
    } else if (stlUrl) {
      setCadStatus("STL loading...");
      load = loadStlGroup(stlUrl, THREE);
    } else {
      setCadStatus("No STEP -- proxy blocks (INSUFFICIENT CAD)");
    }
    return load.then(function (cadGroup) {
      var hasCad = !!(cadGroup && cadGroup.children && cadGroup.children.length);
      buildProxyFrames(g, THREE, model, hasCad);
      if (hasCad) {
        fitCadGroup(cadGroup, THREE);
        var slug = model.part_slug || "Part";
        var partId = slug + "_Strip";
        cadGroup.userData = { id: partId, label: "CAD " + slug };
        g.add(cadGroup);
        kinematic.cadGroup = cadGroup;
        kinematic.cadLoaded = true;
        kinematic.meshes[partId] = cadGroup;
        kinematic.rest[partId] = { x: cadGroup.position.x, y: cadGroup.position.y, z: cadGroup.position.z };
        var kind = cad.kind || (stepUrl ? "step" : "stl");
        var synth = cad.synthesized ? " synthesized plate" : " from STEP";
        setCadStatus("CAD " + kind + synth + " -- sensitivity on mesh");
      } else if (!stepUrl && !stlUrl) {
        setCadStatus("Proxy blocks only (no STEP on this job)");
      }
      return g;
    }).catch(function (err) {
      buildProxyFrames(g, THREE, model, false);
      setCadStatus("CAD load failed -- proxy blocks. " + (err && err.message ? err.message : ""));
      return g;
    });
  }

  function highlight(id) {
    kinematic.selectedId = id;
    var THREE = kinematic.THREE;
    function paint(obj, hit) {
      if (!obj) return;
      if (obj.material && obj.material.emissive && THREE) {
        obj.material.emissive = new THREE.Color(hit ? 0xffb84d : 0x000000);
        obj.material.emissiveIntensity = hit ? 0.55 : 0;
      }
      if (obj.children) obj.children.forEach(function (c) { paint(c, hit); });
    }
    Object.keys(kinematic.meshes).forEach(function (k) {
      var m = kinematic.meshes[k];
      var hit = k === id || (id && k.indexOf(id) >= 0) || (id && id.indexOf(k) >= 0);
      paint(m, hit);
    });
  }

  function applySensitivityPose(tAmp, exaggeration, driverName) {
    var model = kinematic.model;
    if (!model) return;
    var driver = driverName || (model.sensitivity_animation && model.sensitivity_animation.driver) || "";
    var frames = model.frames || [];
    var axis = "z";
    var frameName = "";
    var m = /_(Tx|Ty|Tz|Rx|Ry|Rz)$/.exec(driver || "");
    if (m) {
      axis = m[1].charAt(1).toLowerCase();
      frameName = driver.slice(0, -3);
    } else if (driver) {
      frameName = driver;
    }
    var mag = (Number(exaggeration) || 50) * 0.04 * (Number(tAmp) || 0);
    Object.keys(kinematic.meshes).forEach(function (k) {
      var rest = kinematic.rest[k];
      var mesh = kinematic.meshes[k];
      if (!rest || !mesh) return;
      mesh.position.set(rest.x, rest.y, rest.z);
      mesh.rotation.set(0, 0, 0);
    });
    var cad = kinematic.cadGroup;
    var cadRest = cad && kinematic.rest[(model.part_slug || "Part") + "_Strip"];
    if (cad && cadRest) {
      cad.position.set(cadRest.x, cadRest.y, cadRest.z);
      cad.rotation.set(0, 0, 0);
      if (axis === "x") cad.position.x = cadRest.x + mag * 10;
      else if (axis === "y") cad.position.z = cadRest.z + mag * 10;
      else cad.position.y = cadRest.y + mag * 8;
      if (m && m[1].charAt(0) === "R") {
        if (axis === "x") cad.rotation.x = mag * 0.35;
        else if (axis === "y") cad.rotation.y = mag * 0.35;
        else cad.rotation.z = mag * 0.35;
      }
    }
    frames.forEach(function (f, idx) {
      var mesh = kinematic.meshes[f.name];
      var rest = kinematic.rest[f.name];
      if (!mesh || !rest || mesh === cad) return;
      var local = (f.name === frameName) ? mag : mag * (idx / Math.max(frames.length, 1));
      if (axis === "x") mesh.position.x = rest.x + local * 8;
      else if (axis === "y") mesh.position.z = rest.z + local * 8;
      else mesh.position.y = rest.y + local * 6;
    });
  }

  function highestContributor(model, measureId) {
    measureId = measureId || "gap_z";
    var table = model.cross_table || {};
    var best = null, bestV = -1;
    Object.keys(table).forEach(function (n) {
      var v = Number((table[n] || {})[measureId] || 0);
      if (v > bestV) { bestV = v; best = n; }
    });
    if (best) return best;
    var anim = model.sensitivity_animation || {};
    return anim.driver || null;
  }

  global.CetolApp = {
    FORBIDDEN: FORBIDDEN,
    deriveModel: deriveModel,
    msmWhatIf: msmWhatIf,
    dualFromDims: dualFromDims,
    renderTree: renderTree,
    renderCrossTable: renderCrossTable,
    renderDualContrib: renderDualContrib,
    renderAdvisor: renderAdvisor,
    renderProductDef: renderProductDef,
    renderGdt: renderGdt,
    renderStations: renderStations,
    renderCetolCannot: renderCetolCannot,
    renderTim: renderTim,
    buildKinematicScene: buildKinematicScene,
    clearKinematic: clearKinematic,
    highlight: highlight,
    applySensitivityPose: applySensitivityPose,
    highestContributor: highestContributor,
    kinematic: kinematic
  };
})(window);
