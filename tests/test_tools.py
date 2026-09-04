# -*- coding: utf-8 -*-
"""اختبارات أدوات THE WAY OUT Agent — تعمل بدون Ollama وبدون إنترنت."""

import socket
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agent import Tools, _parse_tool_args  # noqa: E402


def test_write_and_read_file(tmp_path):
    p = tmp_path / "sub" / "hello.txt"
    r1 = Tools.write_file(str(p), "السلام عليكم 👋")
    assert "تم إنشاء" in r1
    assert Tools.read_file(str(p)) == "السلام عليكم 👋"


def test_read_missing_file():
    assert "غير موجود" in Tools.read_file("nope-missing-xyz.txt")


def test_read_directory_returns_hint(tmp_path):
    assert "list_files" in Tools.read_file(str(tmp_path))


def test_list_files(tmp_path):
    (tmp_path / "a.txt").write_text("a", encoding="utf-8")
    (tmp_path / "sub").mkdir()
    out = Tools.list_files(str(tmp_path))
    assert "a.txt" in out and "sub" in out


def test_list_missing_path():
    assert "غير موجود" in Tools.list_files("nope-dir-xyz")


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
    ],
)
def test_execute_blocks_destructive(evil):
    assert "محظور" in Tools.execute_terminal(evil)


def test_check_closed_port():
    # المنفذ 9 (discard) غالباً مغلق — المهم أن الرد منسّق وليس استثناء.
    out = Tools.check_port(9)
    assert "المنفذ 9" in out
    assert ("مغلق" in out) or ("مفتوح" in out)


def test_launch_and_stop_server(tmp_path):
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()

    entry = str(tmp_path / "demo_app.py")
    out = Tools.launch_the_way_out(entry_file=entry, port=port)
    try:
        assert f"localhost:{port}" in out or "تم تشغيل" in out
        assert Path(entry).exists()  # أنشأ السيرفر التجريبي تلقائياً
        assert "المنفذ" in Tools.check_port(port)
    finally:
        Tools.stop_server()


def test_parse_tool_args_dict():
    assert _parse_tool_args({"a": 1}) == {"a": 1}


def test_parse_tool_args_json_string():
    assert _parse_tool_args('{"command": "dir"}') == {"command": "dir"}


def test_parse_tool_args_bad_string():
    assert _parse_tool_args("not-json{{{") == {}
