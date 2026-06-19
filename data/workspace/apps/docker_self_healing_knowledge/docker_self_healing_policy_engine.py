import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class GateResult:
    verdict: str
    score: int
    reasons: list[str] = field(default_factory=list)
    proposed_actions: list[str] = field(default_factory=list)
    required_evidence: list[str] = field(default_factory=list)
    no_go: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "score": self.score,
            "reasons": self.reasons,
            "proposed_actions": self.proposed_actions,
            "required_evidence": self.required_evidence,
            "no_go": self.no_go,
        }


def _num(metrics: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = metrics.get(key, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _flag(metrics: dict[str, Any], key: str) -> bool:
    return bool(metrics.get(key, False))


def evaluate(metrics: dict[str, Any]) -> GateResult:
    result = GateResult(verdict="OBSERVE", score=100)
    unhealthy = _num(metrics, "container_unhealthy_count")
    restart_delta = _num(metrics, "restart_count_delta")
    failure_window = _num(metrics, "repeated_failure_window_min")
    disk_free = _num(metrics, "disk_free_percent", 100.0)
    memory_pressure = _num(metrics, "memory_pressure_percent")
    cpu_pressure = _num(metrics, "cpu_pressure_percent")

    if unhealthy > 0:
        result.score -= min(30, int(unhealthy) * 10)
        result.reasons.append(f"{int(unhealthy)} unhealthy container signal(s) observed.")
        result.required_evidence.extend(["docker ps with health status", "container logs tail", "service endpoint check"])
        result.proposed_actions.append("Prepare a minimal service-specific recovery proposal; do not restart automatically.")

    if restart_delta >= 3 or failure_window >= 10:
        result.score -= 20
        result.reasons.append("Repeated restart/failure window suggests a loop or dependency fault.")
        result.required_evidence.extend(["restart history", "resource metrics", "recent configuration diff"])
        result.proposed_actions.append("Classify root cause before any additional retry; cap retry attempts at 3.")

    if disk_free < 10:
        result.score -= 25
        result.reasons.append(f"Disk free percent is low ({disk_free:.1f}%).")
        result.no_go.append("No image pull, build, or bulk download while disk_free_percent < 10.")
        result.proposed_actions.append("Collect storage inventory and cleanup candidates before restarting heavy services.")

    if memory_pressure >= 90 or cpu_pressure >= 95:
        result.score -= 15
        result.reasons.append("Host resource pressure is too high for safe autonomous repair.")
        result.no_go.append("No self-healing executor under extreme CPU or memory pressure.")
        result.proposed_actions.append("Defer mutation and record host-pressure incident evidence.")

    if _flag(metrics, "port_conflict_detected"):
        result.score -= 15
        result.reasons.append("Port conflict detected.")
        result.required_evidence.extend(["netstat owning process", "live HTTP probe", "service registry expected port"])
        result.proposed_actions.append("Prefer alternate external harness port over killing unknown legacy processes.")

    high_risk = [
        "compose_file_change_requested",
        "destructive_action_requested",
        "cloud_cost_action_requested",
        "stable_workflow_replacement_requested",
    ]
    for key in high_risk:
        if _flag(metrics, key):
            result.score -= 35
            result.no_go.append(f"{key} requires human approval, implementation plan, backup, and rollback.")

    if _flag(metrics, "external_dependency_failure"):
        result.score -= 10
        result.reasons.append("External dependency failure observed.")
        result.proposed_actions.append("Use bounded retry with timeout and preserve progress status outside Docker.")

    approval = _flag(metrics, "human_approval")
    backup = _flag(metrics, "backup_available")
    rollback = _flag(metrics, "rollback_available")
    incident_logged = _flag(metrics, "incident_logged")

    if result.no_go:
        result.verdict = "NO_GO"
    elif result.score < 60:
        result.verdict = "PLAN_REQUIRED"
    elif unhealthy > 0 or restart_delta > 0 or _flag(metrics, "port_conflict_detected"):
        result.verdict = "PROPOSE_ONLY"
    else:
        result.verdict = "OBSERVE"

    if approval and backup and rollback and incident_logged and result.verdict == "PLAN_REQUIRED":
        result.verdict = "APPROVED_DRY_RUN_ONLY"
        result.proposed_actions.append("Run a dry-run executor and compare desired vs actual state before any mutation.")

    if not result.reasons:
        result.reasons.append("No recovery trigger exceeded the observation gate.")
    if not result.proposed_actions:
        result.proposed_actions.append("Continue monitoring and update the knowledge DB only.")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate Docker self-healing/evolution gates from metrics JSON.")
    parser.add_argument("--metrics", type=Path, help="Path to metrics JSON. If omitted, a safe sample is used.")
    parser.add_argument("--out", type=Path, help="Optional output JSON path.")
    args = parser.parse_args()

    if args.metrics:
        metrics = json.loads(args.metrics.read_text(encoding="utf-8"))
    else:
        metrics = {
            "container_unhealthy_count": 1,
            "restart_count_delta": 0,
            "disk_free_percent": 35,
            "port_conflict_detected": False,
            "compose_file_change_requested": False,
            "human_approval": False,
        }
    result = evaluate(metrics).to_dict()
    payload = json.dumps(result, indent=2, ensure_ascii=False)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(payload + "\n", encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
