"""اختبارات LENS Operator v0.1 — السيناريوهات الخمسة المطلوبة."""

import json
from pathlib import Path

import pytest

from lens_operator.memory import ProjectMemory, Evidence, redact, relevance
from lens_operator.operator import LensOperator, needs_approval, check_workspace_scope
from lens_operator.record import Status, TestStatus
from lens_operator.context import load_context


@pytest.fixture()
def ws(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "CHANNEL_BRAIN.md").write_text(
        "# CHANNEL BRAIN\nاستراتيجية LENS: محلي أولاً، صفر تكلفة.",
        encoding="utf-8")
    return tmp_path


def make_op(ws, executor, run_tests=False, approver=None):
    return LensOperator(workspace=ws, memory=ProjectMemory(ws / "memory"),
                        executor=executor, run_tests=run_tests, approver=approver)


# ---------------------------------------------------------------- Test 1
def test_1_create_file_full_cycle(ws):
    """execution + file creation + record + review + memory"""
    def executor(task, ctx):
        (ws / "test_file.txt").write_text("hello", encoding="utf-8")
        return "✅ تم إنشاء الملف test_file.txt"

    rec = make_op(ws, executor).run("create a test file")

    assert rec.status == Status.COMPLETED
    assert (ws / "test_file.txt").exists()                    # file creation
    assert rec.plan and rec.actions                           # plan + actions
    rec_path = ws / "memory" / "executions" / f"{rec.execution_id}.json"
    assert rec_path.exists()                                  # record persisted
    saved = json.loads(rec_path.read_text(encoding="utf-8"))
    assert saved["command"] == "create a test file"
    assert rec.review["score"] > 0 and "answers" in rec.review  # review
    mem = ProjectMemory(ws / "memory")
    assert mem.stats()["learnings"] >= 1                      # memory
    assert mem.project_state()["last_status"] == Status.COMPLETED


def test_1b_context_loads_channel_brain(ws):
    ctx = load_context("راجع الاستراتيجية", ws, ProjectMemory(ws / "memory"))
    assert "docs/CHANNEL_BRAIN.md" in ctx.source_of_truth
    assert "CHANNEL BRAIN" in ctx.as_prompt()


# ---------------------------------------------------------------- Test 2
def test_2_failure_retry_diagnose_record(ws):
    """failure → retry → diagnosis → record"""
    calls = []

    def executor(task, ctx):
        calls.append(ctx)
        return "❌ فشل: ModuleNotFoundError: no module named foo"

    rec = make_op(ws, executor).run("break something")

    assert rec.status == Status.BLOCKED               # لا حلقة لانهائية
    assert len(calls) == 3                            # 1 + MAX_RETRY(2)
    assert rec.retries == 2
    assert "مكتبة ناقصة" in rec.review["diagnosis"]   # diagnosis
    assert any("تشخيص الفشل" in a["description"] for a in rec.actions)
    assert (ws / "memory" / "executions" / f"{rec.execution_id}.json").exists()
    # المحاولة الثانية تُحقن فيها نتيجة الفشل السابق
    assert "محاولة سابقة فشلت" in calls[1]
    assert rec.review["verified"] is False


def test_2b_no_success_claim_without_evidence(ws):
    rec = make_op(ws, lambda t, c: "❌ فشل").run("do something")
    assert rec.status != Status.COMPLETED
    assert "COMPLETED" not in rec.report().split("Status:")[1].split("\n")[0]


# ---------------------------------------------------------------- Test 3
def test_3_second_execution_retrieves_learning(ws):
    """EX1 → Learning → Memory → EX2 retrieves Learning"""
    seen = {}

    def ex1(task, ctx):
        return "❌ فشل: ModuleNotFoundError deploy tool"

    op = make_op(ws, ex1)
    r1 = op.run("نشّط وحدة الفهرسة indexing module")
    assert r1.status == Status.BLOCKED
    assert ProjectMemory(ws / "memory").stats()["learnings"] >= 1

    def ex2(task, ctx):
        seen["ctx"] = ctx
        return "✅ تم"

    op2 = make_op(ws, ex2)
    r2 = op2.run("نشّط وحدة الفهرسة indexing module مرة أخرى")

    assert r2.execution_id != r1.execution_id
    assert r1.execution_id in r2.context["previous_executions"]
    # التعلّم السابق وصل فعلياً لسياق التنفيذ الثاني
    assert any("تجنّب تكرار" in m for m in r2.context["relevant_memory"])
    assert "تجنّب تكرار" in seen["ctx"]
    assert "إخفاقات معروفة" in seen["ctx"]


def test_3b_repeated_pattern_gets_promoted(ws):
    mem = ProjectMemory(ws / "memory")
    mem.ensure_layout()
    for _ in range(3):
        item = mem.add_pattern("نمط: التحقق بعد كل تشغيل")
    assert item["tier"] == Evidence.PROVEN_PATTERN
    assert mem.stats()["proven_patterns"] >= 1


def test_3c_single_observation_is_not_a_fact(ws):
    mem = ProjectMemory(ws / "memory")
    mem.ensure_layout()
    item = mem.add_learning("تجربة واحدة")
    assert item["tier"] == Evidence.LEARNING
    assert item["tier"] != Evidence.FACT


# ---------------------------------------------------------------- Test 4
def test_4_outside_workspace_is_blocked(ws):
    called = []
    rec = make_op(ws, lambda t, c: called.append(1) or "✅").run(
        "اقرأ الملف /etc/passwd وعدّله")

    assert rec.status == Status.BLOCKED
    assert not called                                  # لم يُنفَّذ شيء
    assert "خارج مساحة العمل" in rec.review["diagnosis"]


@pytest.mark.parametrize("cmd", ["read ../../secrets.txt", r"open C:\Windows\x.ini",
                                 "cat ~/.ssh/id_rsa"])
def test_4b_scope_patterns_blocked(ws, cmd):
    assert check_workspace_scope(cmd, ws) is not None


def test_4c_inside_workspace_allowed(ws):
    assert check_workspace_scope("عدّل ملف README.md في docs", ws) is None


# ---------------------------------------------------------------- Test 5
def test_5_human_approval_pauses_execution(ws):
    called = []
    rec = make_op(ws, lambda t, c: called.append(1) or "✅").run(
        "publish the episode to the channel")

    assert rec.status == Status.NEEDS_APPROVAL
    assert not called                                  # توقف قبل التنفيذ
    assert rec.approval["required"] and not rec.approval["granted"]
    assert "Human approval required: YES" in rec.report()


def test_5b_approval_granted_executes(ws):
    called = []
    op = make_op(ws, lambda t, c: called.append(1) or "✅ تم النشر",
                 approver=lambda reason, cmd: True)
    rec = op.run("publish the episode")
    assert rec.approval["granted"] is True
    assert called and rec.status == Status.COMPLETED


@pytest.mark.parametrize("cmd,expected", [
    ("git push origin main", "عملية Git حساسة (push)"),
    ("ادفع اشتراك الاستضافة", "قرار مالي / صرف"),
    ("غيّر الـapi_key", "تغيير secrets"),
    ("اقرأ الملفات", None),
])
def test_5c_human_gates(cmd, expected):
    assert needs_approval(cmd) == expected


# ---------------------------------------------------------------- عام
def test_secrets_are_redacted_from_records(ws):
    rec = make_op(ws, lambda t, c: "✅ تم api_key=sk-abcdef123456").run("اقرأ الإعدادات")
    blob = json.dumps(rec.to_dict(), ensure_ascii=False)
    assert "sk-abcdef123456" not in blob
    assert "REDACTED" in blob


def test_redact_helper():
    assert "sk-1234567890" not in redact("token: sk-1234567890")


def test_tests_failed_blocks_completed_status(ws, monkeypatch):
    op = make_op(ws, lambda t, c: "✅ تم", run_tests=True)
    monkeypatch.setattr(op, "run_tests", lambda: (TestStatus.FAILED, "1 failed"))
    rec = op.run("عدّل شيئاً")
    assert rec.status == Status.FAILED         # Not tested/failed ≠ Passed
    assert any("انحدار" in f for f in rec.review["findings"])


def test_not_run_tests_reported_honestly(ws):
    rec = make_op(ws, lambda t, c: "✅ تم").run("مهمة بسيطة")
    assert rec.tests["status"] == TestStatus.NOT_RUN
    assert any("Not tested" in f or "لم تُشغَّل" in f for f in rec.review["findings"])


def test_dry_run_does_not_execute(ws):
    called = []
    rec = make_op(ws, lambda t, c: called.append(1) or "✅").run("مهمة", dry_run=True)
    assert not called and rec.status == Status.UNKNOWN


def test_relevance_scoring():
    assert relevance("indexing module", "the indexing module failed") > 0
    assert relevance("indexing", "طقس جميل اليوم") == 0


def test_history_and_report_are_readable(ws):
    op = make_op(ws, lambda t, c: "✅ تم")
    op.run("مهمة أولى")
    op.run("مهمة ثانية")
    rows = ProjectMemory(ws / "memory").executions()
    assert [r["execution_id"] for r in rows] == ["EX-000001", "EX-000002"]


def test_cli_status_and_history(ws, capsys):
    from lens_operator.cli import main
    make_op(ws, lambda t, c: "✅ تم").run("مهمة")
    assert main(["-w", str(ws), "status"]) == 0
    assert main(["-w", str(ws), "history"]) == 0
    out = capsys.readouterr().out
    assert "EX-000001" in out


def test_unrecoverable_error_stops_early(ws):
    """خطأ الاتصال بالموديل لا يُعاد 3 مرات — إيقاف مبكر مع إرشاد واضح."""
    calls = []

    def executor(task, ctx):
        calls.append(1)
        return "❌ خطأ في الاتصال بالموديل — تأكد أن Ollama شغال"

    rec = make_op(ws, executor).run("مهمة تحتاج الموديل")
    assert len(calls) == 1                       # لا إعادة محاولة عبثية
    assert rec.status == Status.BLOCKED
    assert "الموديل المحلي غير متاح" in rec.review["diagnosis"]
    assert any("Ollama" in a for a in rec.next_actions)


def test_granted_approval_is_recorded_as_decision(ws):
    op = make_op(ws, lambda t, c: "✅ تم", approver=lambda r, c: True)
    rec = op.run("publish the episode")
    decisions = ProjectMemory(ws / "memory").all_items("decisions")
    assert decisions and "موافقة بشرية" in decisions[0]["text"]
    assert decisions[0]["tier"] == Evidence.FACT
    assert decisions[0]["source_execution"] == rec.execution_id
