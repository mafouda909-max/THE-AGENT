"""LENS Operator — طبقة التشغيل فوق THE WAY OUT local agent.

الدورة:
  Command → Load Context → Plan → Execute → Test → Self-Review → Learn
  → Persist Memory → Report

لا يستبدل `agent.py`؛ يستدعيه كمحرك تنفيذ (harness) ويضيف فوقه
الذاكرة والمراجعة والتعلم والأدلة.
"""

from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path

from .context import ExecutionContext, load_context, git_state
from .memory import Evidence, ProjectMemory
from .record import ExecutionRecord, Status, TestStatus
from .review import self_review

MAX_RETRY = int(os.getenv("LENS_MAX_RETRY", "2"))

#: بوابات بشرية — لا يتجاوزها الـOperator تلقائياً
#: ملاحظة: لا نستخدم \b مع العربية — حدود الكلمات لا تعمل بشكل موثوق مع
#: الحروف العربية الملتصقة (مثل "الـapi_key")؛ نستخدم أنماطاً صريحة بدلاً منها.
HUMAN_GATES = [
    (r"(?:publish|deploy|نشر|انشر|ينشر|ارفع للجمهور)", "نشر محتوى"),
    (r"(?:git\s+push|force[- ]push|بush)", "عملية Git حساسة (push)"),
    (r"(?:\bpay\b|purchase|\bbuy\b|spend|اشتر|ادفع|صرف مال|الصرف)",
     "قرار مالي / صرف"),
    (r"(?:secret|api[_-]?key|apikey|\btoken\b|credential|كلمة السر|المفاتيح)",
     "تغيير secrets"),
    (r"(?:drop\s+(?:table|database)|rm\s+-rf|احذف قاعدة|امسح البيانات|حذف البيانات)",
     "حذف بيانات مهمة"),
    (r"(?:firewall|sudo\s+chmod|security\s+policy|سياسة أمنية|جدار الحماية)",
     "سياسة أمنية حرجة"),
]


def needs_approval(command: str) -> str | None:
    """يرجع سبب الحاجة لموافقة بشرية أو None."""
    low = (command or "").lower()
    for pattern, reason in HUMAN_GATES:
        if re.search(pattern, low):
            return reason
    return None


def _inside_workspace(path: str, workspace: Path) -> bool:
    try:
        Path(workspace, path).resolve().relative_to(workspace.resolve())
        return True
    except (ValueError, OSError):
        return False


def check_workspace_scope(command: str, workspace: Path) -> str | None:
    """يرفض المهام التي تستهدف مسارات خارج مساحة العمل. يرجع سبب المنع أو None."""
    candidates = re.findall(r"(?:^|\s)((?:[A-Za-z]:\\|/|~|\.\./)[^\s\"']*)", command or "")
    for cand in candidates:
        cand = cand.rstrip(".,؛;")
        if cand.startswith("~") or re.match(r"^[A-Za-z]:\\", cand):
            return f"المسار خارج مساحة العمل: {cand}"
        if not _inside_workspace(cand, workspace):
            return f"المسار خارج مساحة العمل: {cand}"
    return None


class LensOperator:
    """المشغّل: ينفذ أمراً واحداً ويُنتج Evidence + Review + Learning + Memory."""

    def __init__(self, workspace: str | Path = ".",
                 memory: ProjectMemory | None = None,
                 executor=None, approver=None, run_tests: bool = True):
        self.workspace = Path(workspace).resolve()
        self.memory = memory or ProjectMemory(self.workspace / "memory")
        self.memory.ensure_layout()
        #: executor(task, context_prompt) -> str  — الافتراضي محرك agent.py
        self.executor = executor or self._default_executor
        #: approver(reason, command) -> bool — الافتراضي: لا موافقة تلقائية
        self.approver = approver
        self.run_tests_enabled = run_tests

    # -- المحرك الافتراضي: agent.py الحالي ------------------------------------
    def _default_executor(self, task: str, context_prompt: str) -> str:
        import agent as _agent  # المحرك الموجود — لا نعيد بناءه

        brain = _agent.get_brain()
        prompt = f"{context_prompt}\n\n## الأمر المطلوب تنفيذه الآن\n{task}"
        return _agent.run_agent(prompt, brain)

    # -- المراحل ---------------------------------------------------------------
    def plan(self, task: str, ctx: ExecutionContext) -> list:
        steps = ["تحميل السياق وذاكرة المشروع"]
        if ctx.known_failures:
            steps.append(f"تجنّب {len(ctx.known_failures)} مسار فشل معروف")
        steps.append(f"تنفيذ المهمة عبر المحرك المحلي: {task[:80]}")
        if self.run_tests_enabled:
            steps.append("تشغيل الاختبارات والتحقق")
        steps += ["مراجعة ذاتية للنتيجة", "استخراج التعلّم وحفظ الذاكرة", "إصدار التقرير"]
        return steps

    def run_tests(self) -> tuple[str, str]:
        if not self.run_tests_enabled:
            return TestStatus.NOT_RUN, "معطّلة"
        if not (self.workspace / "tests").exists():
            return TestStatus.NOT_RUN, "لا يوجد مجلد tests"
        try:
            p = subprocess.run(["python3", "-m", "pytest", "tests/", "-q"],
                               cwd=str(self.workspace), capture_output=True,
                               text=True, timeout=600)
        except Exception as e:  # noqa: BLE001
            return TestStatus.NOT_RUN, f"تعذّر التشغيل: {e}"
        out = (p.stdout + p.stderr)[-3000:]
        if "No module named pytest" in out:
            return TestStatus.NOT_RUN, "pytest غير مثبت"
        return (TestStatus.PASSED if p.returncode == 0 else TestStatus.FAILED), out

    #: أخطاء لا تُصلَح بإعادة المحاولة — نوقف فوراً بدل إهدار المحاولات
    UNRECOVERABLE = ("خطأ في الاتصال", "connection refused", "connectionerror",
                     "ollama", "failed to establish a new connection")

    def diagnose(self, output: str) -> str:
        low = (output or "").lower()
        for needle, msg in (
            ("خطأ في الاتصال", "الموديل المحلي غير متاح (Ollama غير شغال أو الموديل ناقص)"),
            ("connection", "فشل الاتصال بالموديل/الشبكة"),
            ("modulenotfounderror", "مكتبة ناقصة — التثبيت مطلوب قبل إعادة المحاولة"),
            ("permission denied", "صلاحيات غير كافية على المسار"),
            ("timeout", "انتهت المهلة — المهمة أطول من الحد"),
            ("غير موجود", "المورد المطلوب غير موجود"),
            ("لم يستخدم", "الموديل لم ينفّذ أي أداة"),
        ):
            if needle in low:
                return msg
        return "سبب غير محدد من المخرجات"

    def is_unrecoverable(self, output: str) -> bool:
        low = (output or "").lower()
        return any(n in low for n in self.UNRECOVERABLE)

    @staticmethod
    def _looks_failed(output: str) -> bool:
        low = (output or "").strip().lower()
        if not low:
            return True
        return any(k in low for k in ("❌", "فشل", "error", "traceback", "توقفت بعد"))

    def learn(self, record: ExecutionRecord, ctx: ExecutionContext) -> dict:
        """يستخرج التعلّم — كـLearning/Observation، وليس كحقيقة مطلقة."""
        learning = {"what_worked": [], "what_failed": [], "lessons": [],
                    "reusable_patterns": []}
        # الوصف يحمل نص المهمة حتى يكون قابلاً للاسترجاع في التنفيذ التالي
        task_tag = record.command[:60]
        for a in record.actions:
            if a.get("ok") is True:
                learning["what_worked"].append(f"{a['description']} — [{task_tag}]")
            elif a.get("ok") is False:
                learning["what_failed"].append(f"{a['description']} — [{task_tag}]")

        if record.status == Status.COMPLETED:
            lesson = f"نجح المسار: {record.command[:80]} — تكرار نفس النهج مقبول"
            learning["lessons"].append(lesson)
            learning["reusable_patterns"].append(
                f"نمط: '{record.command[:60]}' يُنفَّذ عبر المحرك المحلي مباشرة")
        else:
            reason = record.review.get("diagnosis") or "سبب غير محدد"
            learning["lessons"].append(
                f"تجنّب تكرار: '{record.command[:60]}' فشل — {reason}")
        if (record.tests or {}).get("status") == TestStatus.FAILED:
            learning["lessons"].append("الاختبارات فشلت — لا تعتبر التغيير آمناً")
        return learning

    def persist(self, record: ExecutionRecord) -> None:
        ex = record.execution_id
        for lesson in record.learning.get("lessons", []):
            self.memory.add_learning(lesson, execution_id=ex)
        for fail in record.learning.get("what_failed", []):
            self.memory.add_failure(fail, execution_id=ex)
        for pat in record.learning.get("reusable_patterns", []):
            self.memory.add_pattern(pat, execution_id=ex)
        # الموافقات البشرية قرارات موثّقة (fact) — تُحفظ للرجوع إليها لاحقاً
        if record.approval.get("granted"):
            self.memory.add_decision(
                f"موافقة بشرية مُنحت على: {record.approval.get('reason')} "
                f"للأمر '{record.command[:60]}'", execution_id=ex)
        self.memory.save_project_state({
            "last_execution": ex,
            "last_status": record.status,
            "last_command": record.command,
            "updated_at": record.finished_at,
            "git": record.context.get("git", {}).get("head", ""),
            "totals": self.memory.stats(),
        })
        self.memory.save_execution(record.to_dict())

    # -- الدورة الكاملة ---------------------------------------------------------
    def run(self, command: str, dry_run: bool = False) -> ExecutionRecord:
        t0 = time.time()
        record = ExecutionRecord(
            execution_id=self.memory.next_execution_id(), command=command)

        # 1) Context
        ctx = load_context(command, self.workspace, self.memory)
        record.context = {
            "project_state": ctx.project_state,
            "git": ctx.git,
            "relevant_memory": [i["text"] for i in
                                ctx.relevant_learnings + ctx.proven_patterns],
            "known_failures": [i["text"] for i in ctx.known_failures],
            "previous_executions": [e.get("execution_id")
                                    for e in ctx.previous_executions],
            "source_of_truth": list(ctx.source_of_truth.keys()),
        }
        record.plan = self.plan(command, ctx)

        # 2) Security gate — خارج مساحة العمل = BLOCKED
        scope = check_workspace_scope(command, self.workspace)
        if scope:
            record.add_action(f"رفض أمني: {scope}", ok=False)
            record.finish(Status.BLOCKED)
            record.review = self_review(record, verified=False)
            record.review["diagnosis"] = scope
            record.learning = self.learn(record, ctx)
            record.next_actions = ["أعد صياغة المهمة داخل مساحة العمل فقط"]
            record.duration_s = time.time() - t0
            self.persist(record)
            return record

        # 3) Human gate
        reason = needs_approval(command)
        if reason:
            approved = bool(self.approver(reason, command)) if self.approver else False
            record.approval = {"required": True, "reason": reason,
                               "granted": approved}
            if not approved:
                record.add_action(f"بانتظار موافقة بشرية: {reason}", ok=None)
                record.finish(Status.NEEDS_APPROVAL)
                record.review = self_review(record, verified=None)
                record.learning = self.learn(record, ctx)
                record.next_actions = [f"وافق يدوياً على: {reason} ثم أعد الأمر"]
                record.duration_s = time.time() - t0
                self.persist(record)
                return record
            record.add_action(f"مُنحت موافقة بشرية: {reason}", ok=True)

        if dry_run:
            record.add_action("dry-run: لم يُنفَّذ شيء", ok=None)
            record.finish(Status.UNKNOWN)
            record.review = self_review(record, verified=None)
            record.learning = self.learn(record, ctx)
            record.duration_s = time.time() - t0
            self.persist(record)
            return record

        # 4) Execute + Failure loop (بحد أقصى واضح)
        before = git_state(self.workspace)
        ctx_prompt = ctx.as_prompt()
        output, success = "", False
        for attempt in range(1, MAX_RETRY + 2):
            record.retries = attempt - 1
            try:
                output = str(self.executor(command, ctx_prompt))
            except Exception as e:  # noqa: BLE001
                output = f"❌ استثناء أثناء التنفيذ: {e}"
            failed = self._looks_failed(output)
            record.add_action(
                f"محاولة {attempt}: تنفيذ المهمة عبر المحرك المحلي",
                ok=not failed, detail=output[:500])
            if not failed:
                success = True
                break
            diagnosis = self.diagnose(output)
            record.add_action(f"تشخيص الفشل: {diagnosis}", ok=None)
            if self.is_unrecoverable(output):
                record.add_action(
                    "إيقاف مبكر: الخطأ لا يُصلَح بإعادة المحاولة", ok=None)
                break
            ctx_prompt += (f"\n\n## محاولة سابقة فشلت (لا تكررها)\n"
                           f"{output[:400]}\nالتشخيص: {diagnosis}")

        # 5) Test
        status, results = self.run_tests()
        record.set_tests(status, results)

        after = git_state(self.workspace)
        record.changed_files = sorted(
            set(after.get("dirty_files", [])) - set(before.get("dirty_files", [])))

        # 6) Status — أمين: غير المتحقق منه ليس نجاحاً
        if success and status != TestStatus.FAILED:
            final = Status.COMPLETED
        elif success:
            final = Status.FAILED  # الاختبارات فشلت بعد التغيير
        elif record.retries >= MAX_RETRY or self.is_unrecoverable(output):
            final = Status.BLOCKED
        else:
            final = Status.FAILED
        record.finish(final)

        # 7) Self-review + 8) Learn + 9) Persist
        verified = True if (success and status == TestStatus.PASSED) else (
            False if not success else None)
        record.review = self_review(record, verified=verified)
        if not success:
            record.review["diagnosis"] = self.diagnose(output)
        record.learning = self.learn(record, ctx)
        record.next_actions = self._next_actions(record)
        record.duration_s = time.time() - t0
        self.persist(record)
        return record

    @staticmethod
    def _next_actions(record: ExecutionRecord) -> list:
        acts = []
        diag = (record.review or {}).get("diagnosis", "")
        if record.status == Status.BLOCKED:
            if "Ollama" in diag or "الموديل المحلي غير متاح" in diag:
                acts.append("شغّل Ollama والموديل المطلوب ثم أعد نفس الأمر")
            else:
                acts.append("راجع سبب التوقف في التقرير ثم أعد الأمر بصياغة مختلفة")
        if (record.tests or {}).get("status") == TestStatus.FAILED:
            acts.append("أصلح الاختبارات الفاشلة قبل أي تغيير جديد")
        if (record.tests or {}).get("status") == TestStatus.NOT_RUN:
            acts.append("شغّل الاختبارات للتحقق المستقل")
        if record.changed_files:
            acts.append("راجع الملفات المتغيرة يدوياً قبل الالتزام (commit)")
        return acts or ["لا إجراء مطلوب"]
