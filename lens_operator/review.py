"""Self-Review إلزامي بعد كل تنفيذ — ناجحاً كان أو فاشلاً.

مراجعة قائمة على الأدلة فقط: لا تفترض نجاحاً لم يُتحقق منه.
"""

from __future__ import annotations

from .record import ExecutionRecord, Status, TestStatus

QUESTIONS = [
    "Did I actually complete the requested task?",
    "What changed?",
    "Did the changes solve the problem?",
    "Did I introduce regressions?",
    "Did tests pass?",
    "What remains incomplete?",
    "What could be improved?",
    "What should be remembered?",
    "What should NOT be repeated?",
]


def self_review(record: ExecutionRecord, verified: bool | None = None) -> dict:
    """يقيّم التنفيذ من الأدلة المسجّلة ويرجع dict للـreview."""
    actions = record.actions or []
    ok = [a for a in actions if a.get("ok") is True]
    bad = [a for a in actions if a.get("ok") is False]
    tests = (record.tests or {}).get("status", TestStatus.NOT_RUN)

    findings, answers = [], {}
    score = 0

    # 1) هل اكتملت المهمة فعلاً؟
    completed = record.status == Status.COMPLETED and bool(ok)
    answers[QUESTIONS[0]] = ("نعم — بدليل إجراءات ناجحة مسجّلة" if completed
                             else f"لا / غير مؤكد — الحالة {record.status}")
    score += 40 if completed else 0

    # 2) ما الذي تغيّر؟
    answers[QUESTIONS[1]] = (", ".join(record.changed_files)
                             if record.changed_files else "لا ملفات تغيّرت")

    # 3) هل حُلّت المشكلة؟ (لا نفترض)
    if verified is True:
        answers[QUESTIONS[2]] = "نعم — تم التحقق"
        score += 20
    elif verified is False:
        answers[QUESTIONS[2]] = "لا — التحقق فشل"
        findings.append("التحقق فشل: النتيجة لا تحقق الهدف")
    else:
        answers[QUESTIONS[2]] = "unknown — لم يُتحقق (Unknown ≠ Success)"
        findings.append("لم يتم التحقق المستقل من النتيجة")

    # 4) انحدارات
    if tests == TestStatus.FAILED:
        answers[QUESTIONS[3]] = "نعم على الأرجح — الاختبارات فشلت"
        findings.append("اختبارات فاشلة بعد التغيير — انحدار محتمل")
    elif tests == TestStatus.PASSED:
        answers[QUESTIONS[3]] = "لا مؤشر على انحدار — الاختبارات نجحت"
    else:
        answers[QUESTIONS[3]] = "unknown — لم تُشغَّل الاختبارات"

    # 5) الاختبارات
    answers[QUESTIONS[4]] = tests
    score += {TestStatus.PASSED: 25, TestStatus.NOT_RUN: 5,
              TestStatus.FAILED: 0}[tests]
    if tests == TestStatus.NOT_RUN:
        findings.append("لم تُشغَّل اختبارات (Not tested ≠ Passed)")

    # 6) ما تبقّى
    remaining = list(record.next_actions)
    if bad:
        remaining.append(f"معالجة {len(bad)} إجراء فاشل")
    answers[QUESTIONS[5]] = "; ".join(remaining) if remaining else "لا شيء معروف"

    # 7) التحسين
    improve = []
    if record.retries:
        improve.append(f"تقليل إعادة المحاولات ({record.retries})")
    if not record.plan:
        improve.append("وضع خطة صريحة قبل التنفيذ")
    answers[QUESTIONS[6]] = "; ".join(improve) if improve else "لا مقترحات"
    score += 15 if not bad else 0

    # 8/9) الذاكرة
    answers[QUESTIONS[7]] = "; ".join(record.learning.get("lessons", [])) or "لا دروس"
    answers[QUESTIONS[8]] = ("; ".join(a["description"] for a in bad[:3])
                             or "لا شيء")

    if bad:
        findings.append(f"{len(bad)} إجراء فاشل أثناء التنفيذ")
    if record.status == Status.BLOCKED:
        findings.append("التنفيذ توقف عند حد إعادة المحاولات (blocked)")

    return {"score": max(0, min(100, score)), "findings": findings,
            "answers": answers, "verified": verified}
