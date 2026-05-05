# -*- coding: utf-8 -*-
import json
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

# Import local analyzer
import sys
CORE = Path(__file__).resolve().parents[1] / "core"
sys.path.insert(0, str(CORE))
from spaghetti_analyzer import analyze

st.set_page_config(page_title="スパゲッティ図分析", layout="wide")

st.title("AI IE スパゲッティ図分析 GUI")
st.caption("UWB / BLE / カメラなどから得た X/Y 時系列CSVを解析します。個人監視ではなく、匿名動線・改善前後比較用です。")

trace = st.file_uploader("X/Y時系列CSV", type=["csv"])
layout_file = st.file_uploader("レイアウトJSON", type=["json"])

with st.expander("CSVフォーマット"):
    st.code("timestamp,tag_id,x,y,z,quality,source\n2026-05-01 09:00:00.000,worker_anon_01,1.2,2.3,1.1,0.91,uwb")

if trace and layout_file and st.button("解析実行"):
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        csv_path = td / "trace.csv"
        layout_path = td / "layout.json"
        out_dir = td / "out"
        csv_path.write_bytes(trace.read())
        layout_path.write_bytes(layout_file.read())
        res = analyze(csv_path, layout_path, out_dir)

        st.success("解析完了")
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("スパゲッティ図")
            st.image(str(out_dir / "spaghetti.png"))
        with c2:
            st.subheader("滞在ヒートマップ")
            st.image(str(out_dir / "heatmap.png"))

        st.subheader("タグ別サマリー")
        st.dataframe(pd.read_csv(out_dir / "tag_summary.csv"), use_container_width=True)

        st.subheader("ゾーン滞在")
        st.dataframe(pd.read_csv(out_dir / "zone_dwell_summary.csv"), use_container_width=True)

        st.subheader("ムダ動線候補")
        st.dataframe(pd.read_csv(out_dir / "waste_patterns.csv"), use_container_width=True)

        st.download_button("report.md ダウンロード", (out_dir / "report.md").read_text(encoding="utf-8"), "report.md")
        st.download_button("trace_enriched.csv ダウンロード", (out_dir / "trace_enriched.csv").read_bytes(), "trace_enriched.csv")
