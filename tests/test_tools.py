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
    for alias, canonical in TOOL_ALIASES.items():
        assert hasattr(Tools, alias), alias
        assert canonical in TOOLS_SCHEMA, canonical


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
