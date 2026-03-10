"""
MOSTCalculator — BasicMOST sequence analysis from labeled Therblig segments.

BasicMOST Activity Sequences
─────────────────────────────
1. General Move  (A-B-G-A-B-P-A)   ← pick-and-place; most common factory motion
2. Tool Use      (A-B-G-A-B-P[tool]A-B-P-A)  ← when U (Use) present in move
3. Controlled    (A-B-G-M-X-I-A)   ← tool guided along path (not detected v1)

Index Values (BasicMOST standard)
──────────────────────────────────
A (distance):   0, 1, 3, 6, 10, 16
B (body):       0, 3, 6
G (grasp):      0, 1, 3
P (placement):  0, 1, 3, 6

1 TMU = 0.036 s  →  1 s ≈ 27.8 TMU
"""

from __future__ import annotations

# Therbligs that signal the END of a General Move cycle
_CYCLE_END = {"RL", "ADe", "UDe", "H"}
# Therbligs that indicate tool use inside a move
_TOOL_USE   = {"U", "USE_TOOL"}


class MOSTCalculator:
    """Group labeled segments into BasicMOST General Move sequences."""

    # ── Public API ─────────────────────────────────────────────────────────────

    def analyze(self, labels: list[dict]) -> dict:
        """
        Args:
            labels: output of TherbligLabeler.label() — each dict has
                    label, most_A, most_B, most_G, most_P, most_tmu,
                    duration_sec, is_nva.

        Returns dict:
            sequences   : list of MOST sequence dicts
            total_tmu   : sum of all sequence TMUs
            va_tmu      : VA-only TMU (excluding NVA sequences)
            nva_tmu     : NVA TMU
            efficiency  : va_tmu / total_tmu  (0–1)
            avg_seq_tmu : average TMU per sequence
            summary_rows: list of [seq#, type, A, B, G, P, TMU, time_s] for table
        """
        sequences = self._build_sequences(labels)
        total_tmu = sum(s["tmu"] for s in sequences)
        nva_tmu   = sum(s["tmu"] for s in sequences if s["has_nva"])
        va_tmu    = total_tmu - nva_tmu

        summary_rows = []
        for i, s in enumerate(sequences, 1):
            summary_rows.append([
                i,
                s["seq_type"],
                s["A"], s["B"], s["G"], s["P"],
                s["tmu"],
                round(s["tmu"] * 0.036, 1),   # TMU → seconds
            ])

        return {
            "sequences":    sequences,
            "total_tmu":    round(total_tmu, 1),
            "va_tmu":       round(va_tmu, 1),
            "nva_tmu":      round(nva_tmu, 1),
            "efficiency":   round(va_tmu / max(total_tmu, 1), 3),
            "avg_seq_tmu":  round(total_tmu / max(len(sequences), 1), 1),
            "summary_rows": summary_rows,
        }

    # ── Sequence building ──────────────────────────────────────────────────────

    def _build_sequences(self, labels: list[dict]) -> list[dict]:
        """
        Partition segments into MOST sequences.

        A sequence ends when a cycle-end Therblig (RL, ADe, UDe, H) is found
        or when we run out of segments.  Each sequence gets the worst-case
        (maximum) A, B, G, P indices across its member segments.
        """
        sequences = []
        buffer: list[dict] = []

        for seg in labels:
            buffer.append(seg)
            if seg["label"] in _CYCLE_END:
                sequences.append(self._seq_from_buffer(buffer))
                buffer = []

        if buffer:   # flush remaining
            sequences.append(self._seq_from_buffer(buffer))

        return sequences

    @staticmethod
    def _seq_from_buffer(segs: list[dict]) -> dict:
        """Aggregate a buffer of segments into one MOST sequence dict."""
        A = max(s.get("most_A", 0) for s in segs)
        B = max(s.get("most_B", 0) for s in segs)
        G = max(s.get("most_G", 0) for s in segs)
        P = max(s.get("most_P", 0) for s in segs)

        labels_in_seq = [s["label"] for s in segs]
        has_tool_use  = any(lbl in _TOOL_USE for lbl in labels_in_seq)
        has_nva       = any(s.get("is_nva", False) for s in segs)

        seq_type = "Tool Use" if has_tool_use else "General Move"

        # General Move formula: (A+B+G+A+B+P+A) × 10  (A appears 3 times)
        tmu = (3 * A + 2 * B + G + P) * 10

        # Tool Use adds an extra A+B+P sub-sequence: (A+B+G + A+B+P + A+B+P+A) × 10
        if has_tool_use:
            tool_A = max(s.get("most_A", 0) for s in segs if s["label"] in _TOOL_USE)
            tmu = (3 * A + 2 * B + G + P + tool_A + B + P) * 10

        return {
            "seq_type":   seq_type,
            "labels":     labels_in_seq,
            "A": A, "B": B, "G": G, "P": P,
            "tmu":        round(float(tmu), 1),
            "duration_s": round(sum(s.get("duration_sec", 0) for s in segs), 2),
            "has_nva":    has_nva,
            "start_sec":  segs[0].get("start_sec", 0),
            "end_sec":    segs[-1].get("end_sec", 0),
        }
