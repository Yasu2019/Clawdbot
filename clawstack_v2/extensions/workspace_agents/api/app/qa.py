from pathlib import Path
import pandas as pd

COLUMN_ALIASES = {
    "defect": ["defect", "defects", "不良数", "ng", "NG"],
    "total": ["total", "inspection", "検査数", "sample", "数量"],
    "product": ["product", "product_no", "品番", "製品番号"],
    "lot": ["lot", "lot_no", "ロット", "製造ロットNo."],
}

def _find_col(df: pd.DataFrame, names: list[str]) -> str | None:
    for name in names:
        if name in df.columns:
            return name
    return None

def analyze_csv(path: str, top_n: int = 10) -> dict:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    df = pd.read_csv(p)
    defect_col = _find_col(df, COLUMN_ALIASES["defect"])
    total_col = _find_col(df, COLUMN_ALIASES["total"])
    product_col = _find_col(df, COLUMN_ALIASES["product"])
    lot_col = _find_col(df, COLUMN_ALIASES["lot"])
    if defect_col is None or total_col is None:
        raise ValueError(f"Required columns not found. columns={list(df.columns)}")
    out = df.copy()
    out["defect_count"] = pd.to_numeric(out[defect_col], errors="coerce").fillna(0)
    out["inspection_count"] = pd.to_numeric(out[total_col], errors="coerce").replace(0, pd.NA)
    out["defect_rate"] = (out["defect_count"] / out["inspection_count"]).fillna(0)
    keep = []
    for col in [product_col, lot_col, "defect_count", "inspection_count", "defect_rate"]:
        if col and col in out.columns:
            keep.append(col)
    ranked_rate = out.sort_values("defect_rate", ascending=False).head(top_n)[keep].to_dict(orient="records")
    ranked_count = out.sort_values("defect_count", ascending=False).head(top_n)[keep].to_dict(orient="records")
    return {"top_by_defect_rate": ranked_rate, "top_by_defect_count": ranked_count, "rows": int(len(out))}
