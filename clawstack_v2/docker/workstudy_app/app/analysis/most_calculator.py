"""
MOSTCalculator v2 - Enhanced for 'New MOST' Methodology.
Integrates General Move, Controlled Move, and Tool Use sequence models.
"""

from __future__ import annotations
import json
import os
from pathlib import Path

# Constants for sequence detection
_CYCLE_END = {"RL", "ADe", "UDe", "H", "UNKNOWN"}
_TOOL_USE  = {"U", "USE_TOOL"}
_CONTROLLED_MOVE = {"M", "I", "POSITION_CONTROLLED", "ALIGN"}

class MOSTCalculator:
    """Enhanced MOST calculator using 'New MOST' sequence models."""

    def __init__(self, knowledge_path: str | Path | None = None):
        if knowledge_path is None:
            # Default path relative to the app
            knowledge_path = Path(__file__).resolve().parents[1] / "config" / "most_standard_knowledge.json"
        
        try:
            with open(knowledge_path, "r", encoding="utf-8") as f:
                self.kb = json.load(f)
        except Exception:
            self.kb = {}

    def analyze(self, labels: list[dict]) -> dict:
        """
        Groups labels into sequences and calculates TMUs based on New MOST patterns.
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
                f"A{s['A']} B{s['B']} G{s['G']} P{s['P']}" + (f" M{s['M']} I{s['I']}" if "M" in s else ""),
                s["tmu"],
                round(s["tmu"] * 0.036, 1),
            ])

        return {
            "sequences":    sequences,
            "total_tmu":    round(total_tmu, 1),
            "va_tmu":       round(va_tmu, 1),
            "nva_tmu":      round(nva_tmu, 1),
            "efficiency":   round(va_tmu / max(total_tmu, 1), 3),
            "avg_seq_tmu":  round(total_tmu / max(len(sequences), 1), 1),
            "review_seq_count": sum(1 for s in sequences if s.get("needs_review")),
            "summary_rows": summary_rows,
            "version": "2.0 (New MOST)"
        }

    def _build_sequences(self, labels: list[dict]) -> list[dict]:
        sequences = []
        buffer: list[dict] = []

        for seg in labels:
            buffer.append(seg)
            if seg["label"] in _CYCLE_END:
                sequences.append(self._seq_from_buffer(buffer))
                buffer = []

        if buffer:
            sequences.append(self._seq_from_buffer(buffer))

        return sequences

    def _seq_from_buffer(self, segs: list[dict]) -> dict:
        """Determines sequence type and aggregates indices using New MOST models."""
        A = max(s.get("most_A", 0) for s in segs)
        B = max(s.get("most_B", 0) for s in segs)
        G = max(s.get("most_G", 0) for s in segs)
        P = max(s.get("most_P", 0) for s in segs)
        M = max(s.get("most_M", 0) for s in segs)
        I = max(s.get("most_I", 0) for s in segs)
        X = max(s.get("most_X", 0) for s in segs)

        labels_in_seq = [s["label"] for s in segs]
        has_tool_use  = any(lbl in _TOOL_USE for lbl in labels_in_seq)
        has_controlled = any(lbl in _CONTROLLED_MOVE for lbl in labels_in_seq)
        
        has_nva       = any(s.get("is_nva", False) for s in segs)
        needs_review  = any(s.get("review_required", False) for s in segs)
        avg_confidence = sum(s.get("confidence", 0.0) for s in segs) / max(len(segs), 1)

        # 1. Determine Sequence Model
        if has_tool_use:
            seq_type = "Tool Use"
            # Formula (Approx): A B G A B P (Tool Index) A B P A
            # For simplicity in v2, we take the dominant tool index
            tmu = (3 * A + 2 * B + G + P + 10) * 10 # 10 is a placeholder for Tool sub-seq
        elif has_controlled:
            seq_type = "Controlled Move"
            # Model: A B G M X I A
            tmu = (A + B + G + M + X + I + A) * 10
        else:
            seq_type = "General Move"
            # Model: A B G A B P A
            tmu = (3 * A + 2 * B + G + P) * 10

        if needs_review:
            seq_type += " (Review)"

        res = {
            "seq_type":   seq_type,
            "labels":     labels_in_seq,
            "A": A, "B": B, "G": G, "P": P,
            "tmu":        round(float(tmu), 1),
            "duration_s": round(sum(s.get("duration_sec", 0) for s in segs), 2),
            "has_nva":    has_nva,
            "needs_review": needs_review,
            "avg_confidence": round(avg_confidence, 3),
            "start_sec":  segs[0].get("start_sec", 0),
            "end_sec":    segs[-1].get("end_sec", 0),
        }
        
        if has_controlled:
            res.update({"M": M, "X": X, "I": I})
            
        return res
