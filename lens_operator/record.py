"""Execution Record — سجل الدليل الكامل لكل تنفيذ."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field, asdict

from .memory import redact


class Status:
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    NEEDS_APPROVAL = "needs_approval"
    UNKNOWN = "unknown"

    ALL = (COMPLETED, FAILED, BLOCKED, NEEDS_APPROVAL, UNKNOWN)


class TestStatus:
    PASSED = "passed"
    FAILED = "failed"
    NOT_RUN = "not_run"


@dataclass
class ExecutionRecord:
    execution_id: str = ""
    command: str = ""
    started_at: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%S"))
    finished_at: str = ""
    context: dict = field(default_factory=dict)
    plan: list = field(default_factory=list)
    actions: list = field(default_factory=list)
    changed_files: list = field(default_factory=list)
    commands_run: list = field(default_factory=list)
    tests: dict = field(default_factory=lambda: {"status": TestStatus.NOT_RUN,
                                                 "results": ""})
    review: dict = field(default_factory=dict)
    learning: dict = field(default_factory=lambda: {
        "what_worked": [], "what_failed": [], "lessons": [], "reusable_patterns": []})
    next_actions: list = field(default_factory=list)
    status: str = Status.UNKNOWN
    duration_s: float = 0.0
    retries: int = 0
    approval: dict = field(default_factory=dict)

    # -- تسجيل ---------------------------------------------------------------
    def add_action(self, description: str, ok: bool | None = None,
                   detail: str = "") -> None:
        self.actions.append({
            "at": time.strftime("%H:%M:%S"),
            "description": redact(description),
            "ok": ok,
            "detail": redact(detail)[:500],
        })

    def add_command(self, command: str, exit_code: int | None = None) -> None:
        self.commands_run.append({"command": redact(command), "exit_code": exit_code})

    def set_tests(self, status: str, results: str = "") -> None:
        self.tests = {"status": status, "results": redact(results)[:2000]}

    def finish(self, status: str) -> "ExecutionRecord":
        if status not in Status.ALL:
            status = Status.UNKNOWN
        self.status = status
        self.finished_at = time.strftime("%Y-%m-%dT%H:%M:%S")
        return self

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    # -- التقرير --------------------------------------------------------------
    def report(self) -> str:
        """تقرير نصي أمين — لا يوحي بالنجاح إذا لم تكتمل المهمة."""
        icon = {Status.COMPLETED: "✅", Status.FAILED: "❌", Status.BLOCKED: "🚧",
                Status.NEEDS_APPROVAL: "⏸️", Status.UNKNOWN: "❔"}.get(self.status, "❔")
        L = ["LENS EXECUTION REPORT", "=" * 56,
             f"Execution:   {self.execution_id}",
             f"Command:     {self.command}",
             f"Status:      {icon} {self.status.upper()}",
             f"Duration:    {self.duration_s:.1f}s | Retries: {self.retries}", ""]

        L.append("Plan:")
        L += [f"  {i}. {s}" for i, s in enumerate(self.plan, 1)] or ["  (لا خطة)"]
        L.append("")

        L.append("What I did:")
        for a in self.actions or []:
            mark = "✅" if a.get("ok") else ("❌" if a.get("ok") is False else "•")
            L.append(f"  {mark} {a['description']}")
        if not self.actions:
            L.append("  (لم يُنفَّذ أي إجراء)")
        L.append("")

        L.append("Files changed:")
        L += [f"  - {f}" for f in self.changed_files] or ["  (لا تغييرات)"]
        L.append("")

        t = self.tests or {}
        L.append(f"Tests: {t.get('status', TestStatus.NOT_RUN)}")
        if t.get("results"):
            L.append(f"  {str(t['results']).splitlines()[-1][:200]}")
        L.append("")

        r = self.review or {}
        L.append(f"Self-review: score {r.get('score', 'n/a')}/100")
        for f in r.get("findings", []):
            L.append(f"  - {f}")
        L.append("")

        lg = self.learning or {}
        if lg.get("what_failed"):
            L.append("Problems found:")
            L += [f"  - {x}" for x in lg["what_failed"]]
            L.append("")
        if lg.get("lessons"):
            L.append("What I learned:")
            L += [f"  - {x}" for x in lg["lessons"]]
            L.append("")
        if lg.get("reusable_patterns"):
            L.append("What should be remembered:")
            L += [f"  - {x}" for x in lg["reusable_patterns"]]
            L.append("")

        L.append("Recommended next action:")
        L += [f"  - {x}" for x in self.next_actions] or ["  - (لا شيء)"]
        L.append("")
        need = "YES" if self.status == Status.NEEDS_APPROVAL else "NO"
        L.append(f"Human approval required: {need}")
        if self.approval.get("reason"):
            L.append(f"  Reason: {self.approval['reason']}")
        return "\n".join(L)
