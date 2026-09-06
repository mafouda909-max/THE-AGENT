# -*- coding: utf-8 -*-
"""اختبارات أدوات THE WAY OUT Agent v2.0 — تعمل بدون Ollama وبدون إنترنت."""

import json
import socket
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent import (  # noqa: E402
    TOOL_ALIASES,
    TOOLSET_CORE,
    TOOLS_SCHEMA,
    Tools,
    _parse_tool_args,
    build_tools_schema,
)

# ---------------- 📁 File Operations ----------------

def test_write_and_read_file(tmp_path):
    p = tmp_path / "sub" / "hello.txt"
    r1 = Tools.write_file(str(p), "السلام عليكم 👋")
    assert "تم إنشاء" in r1
    assert Tools.read_file(str(p)) == "السلام عليكم 👋"


def test_read_missing_file():
    assert "غير موجود" in Tools.read_file("nope-missing-xyz.txt")


def test_read_directory_returns_hint(tmp_path):
    assert "list_directory" in Tools.read_file(str(tmp_path))


def test_edit_file(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("hello v1", encoding="utf-8")
    assert "تم تعديل" in Tools.edit_file(str(p), "v1", "v2")
    assert p.read_text(encoding="utf-8") == "hello v2"


def test_edit_file_missing_text(tmp_path):
    p = tmp_path / "a.txt"
    p.write_text("hello", encoding="utf-8")
    assert "غير موجود" in Tools.edit_file(str(p), "zzz", "y")


def test_list_directory(tmp_path):
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    out = Tools.list_directory(str(tmp_path))
    assert "a.txt" in out and "sub" in out


def test_list_missing_path():
    assert "غير موجود" in Tools.list_directory("nope-dir-xyz")


def test_search_files(tmp_path):
    (tmp_path / "a.txt").write_text("needle here", encoding="utf-8")
    (tmp_path / "b.txt").write_text("nothing", encoding="utf-8")
    out = Tools.search_files("needle", str(tmp_path))
    assert "a.txt" in out and "b.txt" not in out.split("a.txt")[0][-50:]


def test_search_files_no_results(tmp_path):
    assert "لا توجد نتائج" in Tools.search_files("zzz-nope", str(tmp_path))


def test_delete_file(tmp_path):
    p = tmp_path / "gone.txt"
    p.write_text("x", encoding="utf-8")
    assert "تم حذف" in Tools.delete_file(str(p))
    assert not p.exists()


def test_delete_missing_file():
    assert "غير موجود" in Tools.delete_file("nope-gone-xyz.txt")


def test_delete_directory_refused(tmp_path):
    assert "مجلد" in Tools.delete_file(str(tmp_path))

# ---------------- 💻 System Operations ----------------

def test_execute_safe_command():
    out = Tools.execute_terminal("echo hello-pytest")
    assert "hello-pytest" in out


@pytest.mark.parametrize(
    "evil",
    [
        "rm -rf /",
        "rm -rf /* --no-preserve-root",
        "format c: /q",
        "del /f /s /q c:\\windows\\x",
        "mkfs.ext4 /dev/sda1",
        "dd if=/dev/zero of=/dev/sda",
        "shutdown -h now",
    ],
)
def test_execute_blocks_destructive(evil):
    assert "محظور" in Tools.execute_terminal(evil)


def test_run_python_code():
    out = Tools.run_python("print(3+4)")
    assert "اشتغل" in out and "7" in out


def test_run_python_file(tmp_path):
    p = tmp_path / "s.py"
    p.write_text("print('from-file')", encoding="utf-8")
    out = Tools.run_python(str(p))
    assert "from-file" in out


def test_run_python_missing_file(tmp_path):
    assert "غير موجود" in Tools.run_python(str(tmp_path / "nope.py"))


def test_run_python_error_reported():
    assert "فشل" in Tools.run_python("raise ValueError('boom')")


def test_check_system_smoke():
    out = Tools.check_system()
    assert "CPU" in out and "Python" in out

# ---------------- 🧠 Memory ----------------

@pytest.fixture()
def mem_env(monkeypatch, tmp_path):
    monkeypatch.setenv("MEMORY_FILE", str(tmp_path / "mem.json"))


def test_memory_roundtrip(mem_env):
    assert "تم الحفظ" in Tools.remember("المستخدم يفضل Flask", "prefs")
    assert "Flask" in Tools.recall("يفضل المستخدم")
    assert "Flask" in Tools.list_memories()
    assert "prefs" in Tools.list_memories("prefs")
    assert "لا توجد" in Tools.list_memories("other")
    assert "تم نسيان" in Tools.forget(1)
    assert "فارغة" in Tools.recall("flask") or "لا توجد" in Tools.recall("flask")


def test_forget_missing(mem_env):
    assert "لا توجد معلومة" in Tools.forget(999)

# ---------------- 🚀 Project Management ----------------

def test_create_project_basic(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    out = Tools.create_project("proj1", "basic")
    assert "تم إنشاء" in out
    assert Path("proj1/app.py").exists()
    assert Path("proj1/README.md").exists()


def test_create_project_bad_template(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    assert "غير معروف" in Tools.create_project("p2", "django-x")


def test_create_project_fuzzy_template(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    out = Tools.create_project("fz1", "basic/flask/fastapi/static")
    assert "تم إنشاء" in out and "فسّرت" in out
    assert Path("fz1/app.py").exists()


def test_basic_template_ascii_safe(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Tools.create_project("ascii1", "basic")
    src = Path("ascii1/app.py").read_text(encoding="utf-8")
    assert all(ord(c) < 128 for c in src), "basic template must be Windows-console safe"


def test_launch_quick_script_reports_not_a_server(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Tools.write_file("quick.py", 'print("done-quick")')
    out = Tools.launch_project(entry_file="quick.py", port=_free_port(), name="nano-test")
    try:
        assert "مش سيرفر" in out
    finally:
        Tools.stop_project("nano-test")


def test_create_project_refuses_nonempty(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    Path("p3").mkdir()
    (Path("p3") / "x.txt").write_text("x", encoding="utf-8")
    assert "غير فارغ" in Tools.create_project("p3", "basic")


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def test_launch_monitor_logs_stop(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    port = _free_port()
    out = Tools.launch_project(entry_file="srv.py", port=port, name="t1")
    try:
        assert f"localhost:{port}" in out or "تم تشغيل" in out
        assert Path("srv.py").exists()
        assert "مفتوح" in Tools.check_health(port)
        assert "آخر" in Tools.read_logs("t1")
        assert "شغال" in Tools.monitor_project("t1")
        api = Tools.call_api(f"http://127.0.0.1:{port}/")
        assert "HTTP 200" in api
    finally:
        Tools.stop_project("t1")


def test_check_closed_port():
    out = Tools.check_health(9)
    assert "المنفذ 9" in out
    assert ("مغلق" in out) or ("مفتوح" in out)


def test_stop_unknown_project():
    assert "لا يوجد" in Tools.stop_project("nope-proj")


def test_monitor_unknown_project():
    assert "غير مسجّل" in Tools.monitor_project("nope-proj")


def test_create_automation_artifact(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    out = Tools.create_automation("manual", "echo hi")
    assert "تم إنشاء" in out
    reg = json.loads(Path("automations.json").read_text(encoding="utf-8"))
    assert reg and reg[0]["action"] == "echo hi"


def test_create_automation_blocks_evil():
    assert "مرفوض" in Tools.create_automation("daily", "rm -rf /")

# ---------------- Aliases (v1.x compat) ----------------

def test_aliases_resolve():
    from agent import resolve_tool_name

    for alias, canonical in TOOL_ALIASES.items():
        assert canonical in TOOLS_SCHEMA, canonical
        assert resolve_tool_name(alias)[0] == canonical, alias


def test_legacy_alias_methods_exist():
    for alias in ("list_files", "read_website", "check_port",
                  "launch_the_way_out", "stop_server"):
        assert callable(getattr(Tools, alias, None)), alias


def test_legacy_check_port():
    out = Tools.check_port(9)
    assert "المنفذ 9" in out


def test_legacy_launch_and_stop(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    port = _free_port()
    out = Tools.launch_the_way_out(entry_file="legacy.py", port=port)
    try:
        assert f"localhost:{port}" in out or "تم تشغيل" in out
    finally:
        Tools.stop_server()

# ---------------- Schema / parsing ----------------

def test_schema_counts():
    full = build_tools_schema("full")
    core = build_tools_schema("core")
    assert len(full) == len(TOOLS_SCHEMA) >= 35
    assert len(core) == len(TOOLSET_CORE) == 7
    assert {t["function"]["name"] for t in core} == set(TOOLSET_CORE)


def test_all_schema_tools_implemented():
    for name in TOOLS_SCHEMA:
        assert callable(getattr(Tools, name, None)), name


def test_parse_tool_args_dict():
    assert _parse_tool_args({"a": 1}) == {"a": 1}


def test_parse_tool_args_json_string():
    assert _parse_tool_args('{"command": "dir"}') == {"command": "dir"}


def test_parse_tool_args_bad_string():
    assert _parse_tool_args("not-json{{{") == {}

# ---------------- 🌐 Frontier & schedule ----------------

def test_frontier_guidance_without_key(monkeypatch):
    import agent as agent_mod

    monkeypatch.setattr(agent_mod, "FRONTIER_API_KEY", "")
    out = Tools.use_frontier_model("ما هي بايثون؟")
    assert "FRONTIER_API_KEY" in out  # توجيهات الإعداد المجاني موجودة


def test_frontier_chat_requires_key(monkeypatch):
    import agent as agent_mod

    monkeypatch.setattr(agent_mod, "FRONTIER_API_KEY", "")
    ok, msg = agent_mod.frontier_chat([{"role": "user", "content": "hi"}])
    assert ok is False and "FRONTIER_API_KEY" in msg


def test_battle_without_any_model(monkeypatch):
    import agent as agent_mod

    monkeypatch.setattr(agent_mod, "FRONTIER_API_KEY", "")
    out = Tools.battle_models("test query")
    assert "Frontier" in out  # يرشد لمفتاح مجاني أو موديل ثانٍ


def test_parse_schedule():
    cron, hm = Tools._parse_schedule("09:30")
    assert cron == "30 9 * * *" and hm == "09:30"
    cron2, _ = Tools._parse_schedule("*/15 * * * *")
    assert cron2 == "*/15 * * * *"
    bad, _ = Tools._parse_schedule("كلام فاضي")
    assert bad is None


def test_schedule_rejects_every_minute(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SCHEDULE_DRY_RUN", "1")
    assert "مرفوضة" in Tools.schedule_task("* * * * *", "echo x")


def test_schedule_dry_run(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("SCHEDULE_DRY_RUN", "1")
    out = Tools.schedule_task("09:30", "echo hello-sched")
    assert "30 9 * * *" in out
    assert "hello-sched" in Path("scheduled_tasks.txt").read_text(encoding="utf-8")


# ---------------- JSON fallback (small models) ----------------

def test_extract_json_block_call():
    from agent import extract_text_tool_calls

    text = '```json\n{"name": "write_file", "arguments": {"path": "a.txt", "content": "hi"}}\n```'
    calls = extract_text_tool_calls(text)
    assert len(calls) == 1
    assert calls[0]["name"] == "write_file"
    assert calls[0]["arguments"] == {"path": "a.txt", "content": "hi"}


def test_extract_unwraps_value_objects():
    from agent import extract_text_tool_calls

    text = '{"name": "write_file", "arguments": {"path": "a.txt", "content": {"type": "string", "value": "hi"}}}'
    calls = extract_text_tool_calls(text)
    assert calls[0]["arguments"]["content"] == "hi"


def test_extract_ignores_unknown_tools_and_plain_text():
    from agent import extract_text_tool_calls

    assert extract_text_tool_calls("نص عادي بدون أي أقواس") == []
    assert extract_text_tool_calls('{"name": "nope_tool", "arguments": {}}') == []


def test_extract_resolves_alias():
    from agent import extract_text_tool_calls

    calls = extract_text_tool_calls('{"name": "check_port", "arguments": {"port": 80}}')
    assert calls and calls[0]["name"] == "check_health"


def test_resolve_tool_name_exact():
    from agent import resolve_tool_name

    assert resolve_tool_name("browse_web")[0] == "browse_web"


def test_resolve_tool_name_alias():
    from agent import resolve_tool_name

    name, note = resolve_tool_name("read_web")
    assert name == "browse_web" and "فسّرت" in note


def test_resolve_tool_name_fuzzy():
    from agent import resolve_tool_name

    name, note = resolve_tool_name("browse_wbe")
    assert name == "browse_web" and "صححت" in note


def test_resolve_tool_name_unknown():
    from agent import resolve_tool_name

    assert resolve_tool_name("nope_xyz_123")[0] is None


def test_extract_invented_name_resolved():
    from agent import extract_text_tool_calls

    calls = extract_text_tool_calls('{"name": "read_web", "arguments": {"url": "https://example.com"}}')
    assert calls and calls[0]["name"] == "browse_web"


def test_auto_summary_loop():
    from agent import _auto_summary

    h = [("write_file", {"path": "a.txt"}, True, "✅ تم الإنشاء"),
         ("read_file", {"path": "a.txt"}, False, "❌ غير موجود")]
    s = _auto_summary(h, 2, 3.0, "loop")
    assert "write_file(a.txt)" in s and "read_file" in s and "📊" in s


def test_auto_summary_empty():
    from agent import _auto_summary

    assert "لم تُنفَّذ" in _auto_summary([], 0, 0.5, "steps")


@pytest.mark.parametrize("q", ["شغّل المشروع", "اكتب ملف x", "launch the server",
                               "ابحث عن بايثون", "افحص المنفذ 5000"])
def test_action_detector_true(q):
    from agent import _looks_like_action

    assert _looks_like_action(q) is True


@pytest.mark.parametrize("q", ["سلام عليكم", "شكرا", "ازاي أشغل المشروع؟",
                               "What is Python?", "تمام"])
def test_action_detector_false(q):
    from agent import _looks_like_action

    assert _looks_like_action(q) is False


def test_match_intent_launch():
    from agent import _match_intent

    assert _match_intent("شغّل مشروع THE WAY OUT") == ("launch_project", {"port": 5000})
    assert _match_intent("شغل السيرفر على 8080") == ("launch_project", {"port": 8080})


def test_match_intent_port():
    from agent import _match_intent

    assert _match_intent("افحص المنفذ 5000") == ("check_health", {"port": 5000})


def test_match_intent_files():
    from agent import _match_intent

    assert _match_intent("اعرض الملفات") == ("list_directory", {})


def test_match_intent_none():
    from agent import _match_intent

    assert _match_intent("اكتب قصيدة عن البحر") is None
    assert _match_intent("سلام عليكم") is None


def test_goal_satisfied_web():
    from agent import _goal_satisfied

    assert _goal_satisfied("اقرأ موقع https://example.com ولخصه", "browse_web") is True
    assert _goal_satisfied("اقرأ موقع https://example.com ولخصه", "delete_file") is False


def test_goal_satisfied_launch():
    from agent import _goal_satisfied

    assert _goal_satisfied("شغّل مشروع THE WAY OUT", "launch_project") is True


def test_goal_tools_empty_for_chitchat():
    from agent import _goal_tools

    assert _goal_tools("سلام عليكم") == set()


def test_goal_summary_contains_result():
    from agent import _goal_summary

    out = _goal_summary("اقرأ موقع", "browse_web", "Example Domain content", 2, 1.0)
    assert "Example Domain content" in out and "browse_web" in out


# ---------------------------------------------------------------- v3.0 العقل القوي
def test_select_brain_local_without_key(monkeypatch):
    import agent

    monkeypatch.setattr(agent, "FRONTIER_API_KEY", "")
    monkeypatch.setenv("AGENT_BRAIN", "auto")
    assert isinstance(agent.select_brain(), agent.AgentBrain)


def test_select_brain_frontier_with_key(monkeypatch):
    import agent

    monkeypatch.setattr(agent, "FRONTIER_API_KEY", "sk-test")
    monkeypatch.setenv("AGENT_BRAIN", "auto")
    brain = agent.select_brain()
    assert isinstance(brain, agent.FrontierBrain)
    assert isinstance(brain.fallback, agent.AgentBrain)


def test_select_brain_forced_local(monkeypatch):
    import agent

    monkeypatch.setattr(agent, "FRONTIER_API_KEY", "sk-test")
    assert isinstance(agent.select_brain(prefer_frontier=False), agent.AgentBrain)


def test_frontier_brain_translates_tool_calls(monkeypatch):
    import agent

    msg = {"role": "assistant", "content": "",
           "tool_calls": [{"function": {"name": "browse_web",
                                        "arguments": '{"url": "https://x.com"}'}}]}
    monkeypatch.setattr(agent, "frontier_chat",
                        lambda *a, **k: (True, msg))
    brain = agent.FrontierBrain(model="test/model")
    out = brain.query([{"role": "user", "content": "hi"}], tools=[])
    assert out["tool_calls"][0]["function"]["name"] == "browse_web"
    assert brain.used_fallback is False


def test_frontier_brain_falls_back_to_local(monkeypatch):
    import agent

    monkeypatch.setattr(agent, "frontier_chat",
                        lambda *a, **k: (False, "خطأ 429: تجاوزت الحد المجاني"))

    class FakeLocal:
        model = "local-test"

        def query(self, messages, tools=None):
            return {"role": "assistant", "content": "من المحلي"}

        def chat_simple(self, prompt, system=None, timeout=180):
            return "محلي"

    brain = agent.FrontierBrain(model="test/model", fallback=FakeLocal())
    out = brain.query([{"role": "user", "content": "hi"}])
    assert out["content"] == "من المحلي"
    assert brain.used_fallback is True
    assert "429" in brain.last_error


def test_frontier_chat_sends_tools(monkeypatch):
    import agent

    captured = {}

    class FakeResp:
        def read(self):
            return json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=0):
        captured["body"] = json.loads(req.data.decode())
        return FakeResp()

    monkeypatch.setattr(agent, "FRONTIER_API_KEY", "sk-test")
    monkeypatch.setattr(agent.urllib.request, "urlopen", fake_urlopen)
    ok, _ = agent.frontier_chat([{"role": "user", "content": "hi"}],
                                model="m", tools=[{"type": "function"}])
    assert ok and captured["body"]["tools"]
    assert captured["body"]["tool_choice"] == "auto"


def test_goal_summary_delivered_on_success_repeat(monkeypatch):
    """الهدف تحقق ثم كرر الموديل نفس النداء → يُسلَّم المحتوى لا قائمة مقتضبة."""
    import agent

    calls = {"n": 0}

    class FakeBrain:
        def query(self, messages, tools=None):
            calls["n"] += 1
            return {"role": "assistant", "content": "",
                    "tool_calls": [{"function": {
                        "name": "browse_web",
                        "arguments": '{"url": "https://example.com"}'}}]}

    monkeypatch.setattr(agent.Tools, "browse_web",
                        staticmethod(lambda url: "📄 محتوى الموقع: Example Domain body"))
    out = agent.run_agent("اقرأ موقع https://example.com ولخصه", FakeBrain())

    assert "Example Domain body" in out          # المحتوى الحقيقي مسلَّم
    assert "browse_web" in out
    assert calls["n"] <= 2                        # وقف بسرعة، مش 3 مرات


def test_safe_print_survives_unencodable_console(monkeypatch, capsys):
    """الإيموجي يجب ألا يُسقط البرنامج على كونسول cp1252."""
    import agent

    class Cp1252Stdout:
        encoding = "cp1252"

        def write(self, text):
            text.encode("cp1252")   # يرفع UnicodeEncodeError على الإيموجي

        def flush(self):
            pass

    monkeypatch.setattr(agent.sys, "stdout", Cp1252Stdout())
    agent.safe_print("❌ نص فيه إيموجي")   # المفروض ما يرفعش استثناء


def test_brain_check_output_is_ascii_safe():
    """مخرجات --brain-check لا تحتوي إيموجي (تُلتقط في متغيرات PowerShell)."""
    import subprocess
    import sys as _s

    p = subprocess.run([_s.executable, "agent.py", "--brain-check"],
                       capture_output=True, text=True, timeout=120)
    out = p.stdout
    assert "[X]" in out or "[OK]" in out
    for ch in ("\u274c", "\u2705"):
        assert ch not in out.splitlines()[0]


def test_frontier_error_surfaces_provider_message(monkeypatch):
    """رسالة المزود الحقيقية يجب ألا تُستبدل بتخمين محلي."""
    import agent
    import io

    body = json.dumps({"error": {"code": 404,
                                 "message": "No endpoints found matching your data policy"}})

    def raise_http(req, timeout=0):
        raise agent.urllib.error.HTTPError(
            "u", 404, "Not Found", {}, io.BytesIO(body.encode()))

    monkeypatch.setattr(agent, "FRONTIER_API_KEY", "sk-test")
    monkeypatch.setattr(agent.urllib.request, "urlopen", raise_http)
    ok, msg = agent.frontier_chat([{"role": "user", "content": "hi"}], model="m/x")
    assert ok is False
    assert "No endpoints found matching your data policy" in msg   # الرسالة الحقيقية
    assert "settings/privacy" in msg                                # الإرشاد الصحيح


def test_frontier_sends_browser_user_agent(monkeypatch):
    """Cloudflare (error 1010) يرفض User-Agent الافتراضي لـurllib."""
    import agent

    captured = {}

    class FakeResp:
        def read(self):
            return json.dumps({"choices": [{"message": {"content": "ok"}}]}).encode()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    def fake_urlopen(req, timeout=0):
        captured["ua"] = req.get_header("User-agent")
        return FakeResp()

    monkeypatch.setattr(agent, "FRONTIER_API_KEY", "sk-test")
    monkeypatch.setattr(agent.urllib.request, "urlopen", fake_urlopen)
    agent.frontier_chat([{"role": "user", "content": "hi"}], model="m")
    assert captured["ua"] and "urllib" not in captured["ua"].lower()
    assert "Mozilla" in captured["ua"]
