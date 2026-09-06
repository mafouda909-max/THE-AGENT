"""Context Loader — يبني سياق التنفيذ من حالة المشروع + الذاكرة السابقة.

القاعدة: لا تحمّل كل شيء عشوائياً — استرجاع بسيط وموثوق فقط.
`docs/CHANNEL_BRAIN.md` هو أعلى مصدر للحقيقة الاستراتيجية إن وُجد.
"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field, asdict
from pathlib import Path

from .memory import ProjectMemory, relevance, redact

#: مصادر الحقيقة مرتبة تنازلياً بالأولوية
SOURCE_OF_TRUTH = [
    "docs/CHANNEL_BRAIN.md",
    "docs/LENS_UNIFIED.md",
    "content/EP01/STATUS_HONEST.md",
    "operations/CONTENT_OS.md",
    "operations/PRODUCTION_PIPELINE.md",
    "operations/ANALYTICS_LEARNING.md",
    "AGENTS.md",
    "THE_WAY_OUT_HANDOVER.md",
    "docs/ROADMAP.md",
    "README.md",
]

MAX_DOC_CHARS = 2500


def _run(cmd: list, cwd: Path, timeout: int = 15) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                           timeout=timeout)
        return p.returncode, (p.stdout + p.stderr).strip()
    except Exception as e:  # noqa: BLE001
        return 1, str(e)


def git_state(workspace: Path) -> dict:
    """حالة Git قبل/بعد التنفيذ. قراءة فقط — لا push ولا عمليات حساسة."""
    if not (workspace / ".git").exists():
        return {"is_repo": False}
    _, branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"], workspace)
    _, head = _run(["git", "rev-parse", "--short", "HEAD"], workspace)
    _, status = _run(["git", "status", "--short"], workspace)
    _, diffstat = _run(["git", "diff", "--stat"], workspace)
    dirty = [ln[3:] for ln in status.splitlines() if ln.strip()]
    return {
        "is_repo": True,
        "branch": branch,
        "head": head,
        "dirty_files": dirty,
        "clean": not dirty,
        "diff_summary": diffstat[-1200:],
    }


@dataclass
class ExecutionContext:
    project_identity: str = ""
    workspace: str = ""
    current_task: str = ""
    project_state: dict = field(default_factory=dict)
    git: dict = field(default_factory=dict)
    source_of_truth: dict = field(default_factory=dict)
    previous_executions: list = field(default_factory=list)
    relevant_learnings: list = field(default_factory=list)
    known_failures: list = field(default_factory=list)
    relevant_decisions: list = field(default_factory=list)
    proven_patterns: list = field(default_factory=list)
    constraints: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    def as_prompt(self, max_chars: int = 4000) -> str:
        """يحوّل السياق لنص مختصر يُحقن في الموديل قبل التخطيط."""
        L = [f"# سياق التنفيذ — {self.project_identity}",
             f"المهمة الحالية: {self.current_task}"]
        g = self.git or {}
        if g.get("is_repo"):
            L.append(f"Git: فرع {g.get('branch')} @ {g.get('head')} — "
                     f"{'نظيف' if g.get('clean') else str(len(g.get('dirty_files', []))) + ' ملف معدّل'}")
        st = self.project_state or {}
        if st:
            L.append("حالة المشروع: " + ", ".join(
                f"{k}={v}" for k, v in list(st.items())[:8]))
        if self.previous_executions:
            L.append("\n## تنفيذات سابقة")
            for e in self.previous_executions[-5:]:
                L.append(f"- {e.get('execution_id')} [{e.get('status')}] "
                         f"{str(e.get('command'))[:90]}")
        for title, items in (("تعلّمات ذات صلة", self.relevant_learnings),
                             ("إخفاقات معروفة — لا تكررها", self.known_failures),
                             ("قرارات سابقة", self.relevant_decisions),
                             ("أنماط مثبتة", self.proven_patterns)):
            if items:
                L.append(f"\n## {title}")
                for it in items:
                    L.append(f"- [{it.get('tier')}] {it.get('text')}")
        if self.constraints:
            L.append("\n## قيود إلزامية")
            L += [f"- {c}" for c in self.constraints]
        if self.source_of_truth:
            L.append("\n## مصادر الحقيقة (مقتطفات)")
            for name, snippet in self.source_of_truth.items():
                L.append(f"### {name}\n{snippet}")
        text = "\n".join(L)
        return text[:max_chars]


DEFAULT_CONSTRAINTS = [
    "العمل محلي فقط داخل مساحة العمل — أي مسار خارجها مرفوض.",
    "ممنوع git push أو أي عملية Git حساسة تلقائياً.",
    "ممنوع النشر أو الصرف المالي أو حذف بيانات مهمة أو تغيير secrets بدون موافقة بشرية.",
    "ممنوع اختراع نتائج: غير المتحقق منه يُسجَّل unknown وليس success.",
]


def load_context(task: str, workspace: Path | str = ".",
                 memory: ProjectMemory | None = None,
                 max_docs: int = 3) -> ExecutionContext:
    workspace = Path(workspace).resolve()
    mem = memory or ProjectMemory(workspace / "memory")

    docs = {}
    for rel in SOURCE_OF_TRUTH:
        p = workspace / rel
        if not p.exists() or not p.is_file():
            continue
        try:
            body = p.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        # CHANNEL_BRAIN دائماً يُحمَّل (أعلى مصدر حقيقة)؛ الباقي حسب الصلة
        always = rel.endswith("CHANNEL_BRAIN.md")
        if always or relevance(task, body[:4000]) > 0.01 or len(docs) < max_docs:
            docs[rel] = redact(body[:MAX_DOC_CHARS])
        if len(docs) >= max_docs + 1:
            break

    return ExecutionContext(
        project_identity=os.getenv("LENS_PROJECT_NAME", "LENS / THE WAY OUT"),
        workspace=str(workspace),
        current_task=task,
        project_state=mem.project_state(),
        git=git_state(workspace),
        source_of_truth=docs,
        previous_executions=mem.executions(limit=5),
        relevant_learnings=mem.relevant(task, "learnings"),
        known_failures=mem.relevant(task, "failures"),
        relevant_decisions=mem.relevant(task, "decisions", limit=3),
        proven_patterns=mem.relevant(task, "proven_patterns", limit=3),
        constraints=list(DEFAULT_CONSTRAINTS),
    )
