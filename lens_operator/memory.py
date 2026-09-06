"""طبقة الذاكرة الدائمة للـOperator — JSONL بسيط وقابل للبحث والتوسع.

لا يعامل أي استنتاج كحقيقة: كل عنصر له درجة ثقة (Evidence tier).
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path


class Evidence:
    """درجات الثقة — من الأضعف للأقوى. لا تُرقّى إلا بأدلة."""

    FACT = "fact"                    # حدث فعلياً ويمكن إثباته
    OBSERVATION = "observation"      # ملاحظة من تنفيذ أو بيانات
    LEARNING = "learning"            # استنتاج من ملاحظة
    HYPOTHESIS = "hypothesis"        # افتراض يحتاج اختباراً
    PATTERN = "pattern"              # نمط تكرر
    PROVEN_PATTERN = "proven_pattern"  # نمط لديه أدلة كافية

    ORDER = [HYPOTHESIS, OBSERVATION, LEARNING, PATTERN, PROVEN_PATTERN, FACT]
    #: عدد المشاهدات المطلوب لترقية learning → pattern → proven_pattern
    PATTERN_THRESHOLD = 2
    PROVEN_THRESHOLD = 3

    @staticmethod
    def tier_for(occurrences: int, base: str = LEARNING) -> str:
        if occurrences >= Evidence.PROVEN_THRESHOLD:
            return Evidence.PROVEN_PATTERN
        if occurrences >= Evidence.PATTERN_THRESHOLD:
            return Evidence.PATTERN
        return base


_STOP = {
    "the", "and", "for", "with", "this", "that", "من", "في", "على", "الى", "إلى",
    "عن", "مع", "هذا", "هذه", "التي", "الذي", "كل", "بعد", "قبل", "ثم", "او", "أو",
}
_SECRET_RE = re.compile(
    r"(?i)(api[_-]?key|secret|token|password|passwd|bearer|sk-[a-z0-9]{8,})"
    r"\s*[:=]?\s*\S*"
)


def redact(text: str) -> str:
    """يمنع تسرب الأسرار إلى سجلات التنفيذ أو الذاكرة."""
    return _SECRET_RE.sub(lambda m: f"{m.group(1)}=***REDACTED***", str(text or ""))


def keywords(text: str) -> set:
    words = re.findall(r"[\w\u0600-\u06FF]{3,}", (text or "").lower())
    return {w for w in words if w not in _STOP}


def relevance(query: str, text: str) -> float:
    """تشابه بسيط وموثوق (Jaccard على الكلمات) — كافٍ لـv0.1."""
    a, b = keywords(query), keywords(text)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


@dataclass
class MemoryItem:
    id: str = ""
    kind: str = "learning"          # learning|failure|decision|pattern|state
    tier: str = Evidence.LEARNING
    text: str = ""
    source_execution: str = ""
    occurrences: int = 1
    tags: list = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


class ProjectMemory:
    """ذاكرة المشروع: تعلّمات، إخفاقات، قرارات، أنماط، وحالة المشروع.

    التخزين JSONL داخل `memory/` (أقل تغيير معماري، قابل للقراءة والبحث و git-diff).
    """

    KINDS = ("learnings", "failures", "decisions", "patterns", "proven_patterns")

    def __init__(self, root: str | Path | None = None):
        self.root = Path(root or os.getenv("LENS_MEMORY_DIR", "memory")).resolve()
        self.executions_dir = self.root / "executions"
        self.state_path = self.root / "project_state" / "state.json"

    # -- تخزين منخفض المستوى ------------------------------------------------
    def _path(self, kind: str) -> Path:
        return self.root / f"{kind}.jsonl"

    def _read(self, kind: str) -> list:
        p = self._path(kind)
        if not p.exists():
            return []
        out = []
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return out

    def _write_all(self, kind: str, items: list) -> None:
        p = self._path(kind)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(
            "".join(json.dumps(i, ensure_ascii=False) + "\n" for i in items),
            encoding="utf-8",
        )

    def ensure_layout(self) -> None:
        (self.root / "project_state").mkdir(parents=True, exist_ok=True)
        self.executions_dir.mkdir(parents=True, exist_ok=True)
        for kind in self.KINDS:
            self._path(kind).touch(exist_ok=True)

    # -- كتابة --------------------------------------------------------------
    def add(self, kind: str, text: str, tier: str = Evidence.LEARNING,
            execution_id: str = "", tags: list | None = None) -> dict:
        """يضيف عنصراً؛ لو مكرر يزيد عدّاد المشاهدات ويرقّي درجة الثقة."""
        text = redact((text or "").strip())
        if not text:
            raise ValueError("لا يمكن حفظ عنصر ذاكرة فارغ")
        items = self._read(kind)
        norm = " ".join(text.lower().split())
        for it in items:
            if " ".join(str(it.get("text", "")).lower().split()) == norm:
                it["occurrences"] = int(it.get("occurrences", 1)) + 1
                it["tier"] = Evidence.tier_for(it["occurrences"], it.get("tier", tier))
                it["updated_at"] = _now()
                self._write_all(kind, items)
                return it
        item = MemoryItem(
            id=f"{kind[:3].upper()}-{len(items) + 1:05d}",
            kind=kind.rstrip("s"),
            tier=tier,
            text=text,
            source_execution=execution_id,
            tags=tags or [],
            created_at=_now(),
            updated_at=_now(),
        ).to_dict()
        items.append(item)
        self._write_all(kind, items)
        return item

    def add_learning(self, text, execution_id="", tier=Evidence.LEARNING, tags=None):
        return self.add("learnings", text, tier, execution_id, tags)

    def add_failure(self, text, execution_id="", tags=None):
        return self.add("failures", text, Evidence.OBSERVATION, execution_id, tags)

    def add_decision(self, text, execution_id="", tags=None):
        return self.add("decisions", text, Evidence.FACT, execution_id, tags)

    def add_pattern(self, text, execution_id="", tags=None):
        item = self.add("patterns", text, Evidence.PATTERN, execution_id, tags)
        if item.get("tier") == Evidence.PROVEN_PATTERN:
            self.add("proven_patterns", item["text"], Evidence.PROVEN_PATTERN,
                     execution_id, tags)
        return item

    def save_execution(self, record: dict) -> Path:
        self.executions_dir.mkdir(parents=True, exist_ok=True)
        path = self.executions_dir / f"{record.get('execution_id', 'EX-UNKNOWN')}.json"
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2),
                        encoding="utf-8")
        idx = self.root / "executions.jsonl"
        summary = {
            "execution_id": record.get("execution_id"),
            "command": record.get("command"),
            "status": record.get("status"),
            "started_at": record.get("started_at"),
            "finished_at": record.get("finished_at"),
            "changed_files": record.get("changed_files", []),
            "tests": (record.get("tests") or {}).get("status"),
            "score": (record.get("review") or {}).get("score"),
        }
        with idx.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(summary, ensure_ascii=False) + "\n")
        return path

    def save_project_state(self, state: dict) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2),
                                   encoding="utf-8")

    # -- قراءة / استرجاع -----------------------------------------------------
    def project_state(self) -> dict:
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                return {}
        return {}

    def executions(self, limit: int = 0) -> list:
        idx = self.root / "executions.jsonl"
        items = []
        if idx.exists():
            for line in idx.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    try:
                        items.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return items[-limit:] if limit else items

    def load_execution(self, execution_id: str) -> dict:
        p = self.executions_dir / f"{execution_id}.json"
        if not p.exists():
            return {}
        return json.loads(p.read_text(encoding="utf-8"))

    def next_execution_id(self) -> str:
        return f"EX-{len(self.executions()) + 1:06d}"

    def all_items(self, kind: str) -> list:
        return self._read(kind)

    def relevant(self, query: str, kind: str, limit: int = 5,
                 min_score: float = 0.04) -> list:
        """استرجاع بسيط وموثوق: تشابه كلمات + ترجيح درجة الثقة والتكرار."""
        scored = []
        for it in self._read(kind):
            base = relevance(query, it.get("text", ""))
            tier_bonus = 0.05 * Evidence.ORDER.index(
                it.get("tier", Evidence.LEARNING)) if it.get(
                "tier") in Evidence.ORDER else 0.0
            score = base + tier_bonus + 0.02 * min(int(it.get("occurrences", 1)), 5)
            if base >= min_score or it.get("tier") in (
                    Evidence.PROVEN_PATTERN, Evidence.FACT):
                scored.append((score, it))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [it for _, it in scored[:limit]]

    def stats(self) -> dict:
        out = {"executions": len(self.executions())}
        for kind in self.KINDS:
            out[kind] = len(self._read(kind))
        return out
