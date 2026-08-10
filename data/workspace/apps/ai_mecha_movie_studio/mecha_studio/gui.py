# -*- coding: utf-8 -*-
from __future__ import annotations
import json
import queue
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
from .core.paths import WORKSPACE
from .core.scanner import scan
from .core.planner import decide
from .core.jsonio import save_json
from .core.project import create_sample_project
from .core.pipeline import run_smoke
from .adapters.comfyui import health as comfy_health


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AI MECHA MOVIE STUDIO V3")
        self.geometry("1000x760")
        self.minsize(850, 650)
        self.scan_report = None
        # ワーカースレッドからのUI更新はキュー経由でメインスレッドへ渡す
        self._ui_queue = queue.Queue()
        self._build()
        self.after(100, self._drain_ui_queue)

    def _build(self):
        top = ttk.Frame(self, padding=10)
        top.pack(fill="x")
        ttk.Label(top, text="AI MECHA MOVIE STUDIO V3", font=("Yu Gothic UI", 16, "bold")).grid(row=0, column=0, columnspan=4, sticky="w")
        ttk.Label(top, text="既存環境を壊さず、AIに『融合 / 単独 / ハイブリッド』を検討させます。", font=("Yu Gothic UI", 10)).grid(row=1, column=0, columnspan=4, sticky="w", pady=(2, 10))

        ttk.Label(top, text="追加探索ルート（;区切り）").grid(row=2, column=0, sticky="w")
        self.roots = ttk.Entry(top, width=90)
        self.roots.grid(row=2, column=1, columnspan=3, sticky="ew")

        ttk.Label(top, text="Ollama URL").grid(row=3, column=0, sticky="w")
        self.ollama_url = ttk.Entry(top, width=40)
        self.ollama_url.insert(0, "http://127.0.0.1:11434")
        self.ollama_url.grid(row=3, column=1, sticky="ew", padx=(5, 15))
        ttk.Label(top, text="モデル").grid(row=3, column=2, sticky="e")
        self.ollama_model = ttk.Entry(top, width=25)
        self.ollama_model.insert(0, "qwen3:8b")
        self.ollama_model.grid(row=3, column=3, sticky="ew", padx=(5, 0))

        for i in range(4):
            top.columnconfigure(i, weight=1 if i in (1, 3) else 0)

        btns = ttk.Frame(self, padding=(10, 0, 10, 10))
        btns.pack(fill="x")
        ttk.Button(btns, text="1. システム検出", command=self.do_scan).pack(side="left", padx=4)
        ttk.Button(btns, text="2. AIに構成判定を依頼", command=self.do_plan).pack(side="left", padx=4)
        ttk.Button(btns, text="3. サンプルプロジェクト生成", command=self.do_project).pack(side="left", padx=4)
        ttk.Button(btns, text="4. 疎通テスト", command=self.do_smoke).pack(side="left", padx=4)
        ttk.Button(btns, text="ComfyUI確認", command=self.do_comfy).pack(side="left", padx=4)

        self.status = ttk.Label(self, text="準備完了", padding=(10, 0))
        self.status.pack(fill="x")
        self.text = tk.Text(self, wrap="word", font=("Yu Gothic UI", 10))
        self.text.pack(fill="both", expand=True, padx=10, pady=10)
        self.log("README_JA.md を先にご確認ください。\n")

    def _drain_ui_queue(self):
        try:
            while True:
                kind, payload = self._ui_queue.get_nowait()
                if kind == "log":
                    self.text.insert("end", payload + ("\n" if not payload.endswith("\n") else ""))
                    self.text.see("end")
                elif kind == "status":
                    self.status.config(text=payload)
        except queue.Empty:
            pass
        self.after(100, self._drain_ui_queue)

    def log(self, s):
        self._ui_queue.put(("log", s))

    def set_status(self, s):
        self._ui_queue.put(("status", s))

    def _thread(self, fn):
        threading.Thread(target=fn, daemon=True).start()

    def do_scan(self):
        # ウィジェットの読み取りはメインスレッドで行う（Tkはスレッド安全ではない）
        roots = [x.strip() for x in self.roots.get().split(";") if x.strip()]

        def work():
            try:
                self.set_status("システム検出中...")
                rep = scan(roots)
                self.scan_report = rep
                save_json(WORKSPACE / "system_scan.json", rep)
                self.log(json.dumps(rep, ensure_ascii=False, indent=2))
                self.set_status("検出完了: workspace/system_scan.json")
            except Exception as e:
                self.log("システム検出失敗: " + str(e))
                self.set_status("システム検出失敗")
        self._thread(work)

    def do_plan(self):
        # ウィジェットの読み取りはメインスレッドで行う（Tkはスレッド安全ではない）
        base_url = self.ollama_url.get().strip()
        model = self.ollama_model.get().strip()

        def work():
            try:
                if self.scan_report is None:
                    self.scan_report = scan([])
                    save_json(WORKSPACE / "system_scan.json", self.scan_report)
                self.set_status("AIが構成を検討中...")
                plan = decide(self.scan_report, base_url, model)
                save_json(WORKSPACE / "integration_plan.json", plan)
                self.log("\n=== AI ARCHITECTURE PLAN ===\n" + json.dumps(plan, ensure_ascii=False, indent=2))
                if plan.get("reuse_unverified"):
                    self.log("※ 未検出のまま再利用候補に挙がった項目: "
                             + ", ".join(str(x) for x in plan["reuse_unverified"]))
                self.set_status("判定完了: workspace/integration_plan.json")
            except Exception as e:
                self.log("構成判定失敗: " + str(e))
                self.set_status("構成判定失敗")
        self._thread(work)

    def do_project(self):
        try:
            p = create_sample_project()
            self.log(f"\nサンプルプロジェクトを生成しました: {p}")
            self.set_status(str(p))
        except Exception as e:
            messagebox.showerror("エラー", str(e))

    def do_smoke(self):
        def work():
            try:
                p = WORKSPACE / "sample_mecha_movie"
                if not (p / "project.json").exists():
                    p = create_sample_project()
                rep = run_smoke(p)
                self.log("\n=== SMOKE TEST ===\n" + json.dumps(rep, ensure_ascii=False, indent=2))
                self.set_status("疎通テスト完了")
            except Exception as e:
                self.log("疎通テスト失敗: " + str(e))
                self.set_status("疎通テスト失敗")
        self._thread(work)

    def do_comfy(self):
        def work():
            ok = comfy_health()
            self.log(f"ComfyUI API http://127.0.0.1:8188 : {'OK' if ok else '未接続'}")
        self._thread(work)


def main():
    App().mainloop()
