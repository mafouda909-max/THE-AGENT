#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 THE WAY OUT Agent — Local Autonomous AI Agent
=================================================
مهندس برمجي ومساعد ذكي ذاتي التشغيل يعمل محلياً بالكامل
عبر Ollama — بدون إنترنت إلزامي وبدون اشتراكات مدفوعة.

التشغيل (Windows PowerShell):
    cd the_way_out
    pip install -r requirements.txt   # أول مرة فقط
    python agent.py                   # وضع تفاعلي
    python agent.py --once "اكتب ملف hello.py"   # أمر واحد
    python agent.py --check           # فحص ذاتي بدون موديل

الإعداد عبر متغيرات البيئة (أو ملف .env — انظر .env.example):
    OLLAMA_BASE_URL=http://localhost:11434
    OLLAMA_MODEL=qwen2.5-coder:1.5b
    AGENT_MAX_STEPS=5
    AGENT_TIMEOUT=60
    DEFAULT_PORT=5000
"""

from __future__ import annotations

import argparse
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

__version__ = "1.1.0"

# ---------------------------------------------------------------------------
# تهيئة اختيارية: colorama للألوان + dotenv لمتغيرات البيئة
# الكود يعمل حتى لو لم تُثبَّت هذه المكتبات بعد (graceful fallback).
# ---------------------------------------------------------------------------
try:
    from colorama import Fore, Style, init as _color_init

    _color_init(autoreset=True)
except Exception:  # pragma: no cover - يعمل بدون ألوان

    class _Dummy:
        def __getattr__(self, _name: str) -> str:
            return ""

    Fore = Style = _Dummy()  # type: ignore

try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except Exception:
    pass  # .env اختياري — نكمل بقيم os.environ الافتراضية

# ---------------------------------------------------------------------------
# الإعدادات
# ---------------------------------------------------------------------------
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:1.5b")
AGENT_MAX_STEPS = int(os.getenv("AGENT_MAX_STEPS", "5"))
AGENT_TIMEOUT = int(os.getenv("AGENT_TIMEOUT", "60"))
DEFAULT_PORT = int(os.getenv("DEFAULT_PORT", "5000"))

SYSTEM_PROMPT = (
    "أنت THE WAY OUT Agent - مهندس برمجي محلي ومساعد ذكي. "
    "نفذ المطلوب باستخدام الـ tools المتاحة وتحدث بالعربي. "
    "القواعد: (1) نفّذ الأدوات بالترتيب المنطقي ولا تطلب تأكيداً لكل خطوة. "
    "(2) لو فشل أمر، جرّب بديلاً مرة واحدة ثم لخّص المشكلة بوضوح. "
    "(3) لا تعرض كلمات سر أو مفاتيح. "
    "(4) في نهاية التنفيذ قدّم ملخصاً قصيراً بالعربي لما تم."
)


# ===========================================================================
# الأدوات (Tools)
# ===========================================================================
class Tools:
    """مجموعة الأدوات التي يستدعيها الموديل ذاتياً (Tool Calling)."""

    RUNNING_PROCESSES: dict = {}

    # أوامر/أنماط تدميرية محظورة — تُفحص قبل أي تنفيذ (case-insensitive).
    BLOCKED_PATTERNS = [
        "rm -rf /",
        "rm -rf /*",
        "rm -rf ~",
        ":(){:|:&};:",
        "mkfs",
        "dd if=",
        "dd of=/dev/",
        "> /dev/sda",
        "format c:",
        "format d:",
        "del /f /s /q c:\\",
        "del /s /q c:\\windows",
        "rmdir /s /q c:\\windows",
        "rd /s /q c:\\windows",
        "remove-item c:\\* -recurse",
        "remove-item c:\\windows",
        "diskpart",
        "shutdown /s",
        "shutdown -h now",
        "poweroff",
        "init 0",
        "init 6",
        "chmod -r 777 /",
        "chown -r ",
        "takeown /f c:\\windows",
    ]

    # حد أقصى لحجم المخرجات حتى لا ينفجر سياق الموديل الصغير (1.5b).
    MAX_OUTPUT = 4000
    MAX_FILE_READ = 3000

    # -- helpers ----------------------------------------------------------
    @staticmethod
    def _is_blocked(command: str) -> str | None:
        lowered = command.lower().strip()
        for pat in Tools.BLOCKED_PATTERNS:
            if pat in lowered:
                return pat
        return None

    @staticmethod
    def _truncate(text: str, limit: int) -> str:
        text = str(text)
        if len(text) > limit:
            return text[:limit] + f"\n… (تم قص {len(text) - limit} حرف — الناتج طويل)"
        return text

    # -- tools ------------------------------------------------------------
    @staticmethod
    def execute_terminal(command: str) -> str:
        """تنفيذ أمر تيرمينال في جهاز المستخدم (مع فلتر أمان)."""
        blocked = Tools._is_blocked(command)
        if blocked:
            return f"⛔ أمر محظور لأسباب أمنية (تطابق مع: `{blocked}`) — لن يُنفَّذ."
        try:
            res = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=AGENT_TIMEOUT,
            )
            out = res.stdout.strip() or res.stderr.strip() or "(تم التنفيذ بدون مخرجات)"
            if res.returncode != 0:
                out = f"⚠️ خرج الكود {res.returncode}:\n{out}"
            return Tools._truncate(out, Tools.MAX_OUTPUT)
        except subprocess.TimeoutExpired:
            return f"⏱️ انتهت المهلة ({AGENT_TIMEOUT}s) قبل اكتمال الأمر."
        except Exception as e:  # noqa: BLE001
            return f"❌ فشل التنفيذ: {e}"

    @staticmethod
    def write_file(path: str, content: str) -> str:
        """كتابة أو تعديل ملف في الجهاز (ينشئ المجلدات تلقائياً)."""
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return f"✅ تم إنشاء وحفظ الملف: `{path}`"
        except Exception as e:  # noqa: BLE001
            return f"❌ فشل حفظ الملف `{path}`: {e}"

    @staticmethod
    def read_file(path: str) -> str:
        """قراءة ملف من الجهاز (أول 3000 حرف)."""
        p = Path(path)
        if not p.exists():
            return f"❌ الملف `{path}` غير موجود."
        if p.is_dir():
            return f"ℹ️ `{path}` مجلد وليس ملفاً — استخدم list_files لعرض محتوياته."
        try:
            return p.read_text(encoding="utf-8", errors="ignore")[: Tools.MAX_FILE_READ]
        except Exception as e:  # noqa: BLE001
            return f"❌ فشل قراءة الملف `{path}`: {e}"

    @staticmethod
    def list_files(path: str = ".") -> str:
        """عرض محتويات مجلد (ملفات ومجلدات فرعية)."""
        p = Path(path)
        if not p.exists():
            return f"❌ المسار `{path}` غير موجود."
        if not p.is_dir():
            return f"ℹ️ `{path}` ملف وليس مجلداً — استخدم read_file لقراءته."
        try:
            entries = sorted(p.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
            if not entries:
                return f"📁 المجلد `{path}` فارغ."
            lines = []
            for e in entries[:100]:
                icon = "📁" if e.is_dir() else "📄"
                size = ""
                if e.is_file():
                    try:
                        size = f" ({e.stat().st_size} بايت)"
                    except OSError:
                        pass
                lines.append(f"{icon} {e.name}{size}")
            extra = f"\n… +{len(entries) - 100} عنصر آخر" if len(entries) > 100 else ""
            return f"📁 محتويات `{path}` ({len(entries)} عنصر):\n" + "\n".join(lines) + extra
        except Exception as e:  # noqa: BLE001
            return f"❌ فشل عرض المجلد `{path}`: {e}"

    @staticmethod
    def check_port(port: int, host: str = "localhost") -> str:
        """فحص هل منفذ/خدمة شغالة أم لا."""
        try:
            with socket.create_connection((host, int(port)), timeout=3):
                return f"🟢 المنفذ {port} على {host} **مفتوح** — الخدمة شغالة. ✅"
        except (OSError, ValueError, OverflowError) as e:
            return f"🔴 المنفذ {port} على {host} **مغلق/لا يستجيب** ({e})."
        except Exception as e:  # noqa: BLE001
            return f"❌ تعذّر فحص المنفذ {port}: {e}"

    @staticmethod
    def launch_the_way_out(entry_file: str = "app.py", port: int = 5000) -> str:
        """تشغيل مشروع THE WAY OUT محلياً (ينشئ سيرفر تجريبي لو الملف غير موجود)."""
        try:
            port = int(port)
        except (TypeError, ValueError):
            port = DEFAULT_PORT

        # أوقف أي نسخة سابقة شغّلها الإيجنت لتفادي تعارض المنافذ.
        old = Tools.RUNNING_PROCESSES.get("wayout")
        if old is not None and old.poll() is None:
            try:
                old.terminate()
                old.wait(timeout=5)
            except Exception:
                try:
                    old.kill()
                except Exception:
                    pass

        if not Path(entry_file).exists():
            demo_code = f'''"""THE WAY OUT — demo server (auto-generated by agent)."""
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = {port}

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        body = (
            "<h1>🚀 THE WAY OUT Project is Running Locally!</h1>"
            f"<p>Agent is working perfectly on port {port}.</p>"
        )
        self.wfile.write(body.encode("utf-8"))

if __name__ == "__main__":
    print(f"Server starting on port {{PORT}}...", flush=True)
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
'''
            Tools.write_file(entry_file, demo_code)

        try:
            proc = subprocess.Popen(
                [sys.executable, entry_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except Exception as e:  # noqa: BLE001
            return f"❌ فشل تشغيل `{entry_file}`: {e}"

        Tools.RUNNING_PROCESSES["wayout"] = proc
        time.sleep(1.5)

        # هل السيرفر فعلاً بيستجيب؟
        if proc.poll() is not None:
            err = ""
            try:
                _, err_b = proc.communicate(timeout=3)
                err = (err_b or b"").decode("utf-8", errors="ignore")[:500]
            except Exception:
                pass
            return f"❌ السيرفر توقف فور تشغيله. الخطأ:\n{err or '(لا توجد رسالة خطأ)'}"

        status = Tools.check_port(port)
        if "مفتوح" in status:
            return f"🚀 تم تشغيل مشروع THE WAY OUT بنجاح على http://localhost:{port}"
        return (
            f"⚠️ تم إطلاق العملية (PID={proc.pid}) لكن المنفذ {port} لا يستجيب بعد. "
            f"جرّب: افحص المنفذ {port} — أو اقرأ الملف {entry_file}."
        )

    @staticmethod
    def read_website(url: str) -> str:
        """قراءة وتصفح أي موقع على الإنترنت وتلخيص محتواه النصي."""
        if not re.match(r"^https?://", url.strip(), re.IGNORECASE):
            url = "http://" + url.strip()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as response:
                raw = response.read()
                charset = response.headers.get_content_charset() or "utf-8"
                html = raw.decode(charset, errors="ignore")

            # الأفضل: BeautifulSoup لو متثبتة — وإلا نرجع لتعقيم regex.
            try:
                from bs4 import BeautifulSoup  # type: ignore

                soup = BeautifulSoup(html, "html.parser")
                for tag in soup(["script", "style", "noscript"]):
                    tag.decompose()
                text = soup.get_text(separator=" ", strip=True)
            except ImportError:
                text = re.sub(r"<script.*?</script>", " ", html, flags=re.S | re.I)
                text = re.sub(r"<style.*?</style>", " ", text, flags=re.S | re.I)
                text = re.sub(r"<[^<]+?>", " ", text)
                text = " ".join(text.split())

            clean = " ".join(text.split())
            if not clean:
                return "ℹ️ تم فتح الصفحة لكن لم يُستخرج نص (قد تكون صفحة JS تفاعلية)."
            return f"📄 محتوى الموقع ({url}):\n{clean[:2000]}"
        except Exception as e:  # noqa: BLE001
            return f"❌ فشل فتح الرابط {url}: {e}"

    @staticmethod
    def stop_server() -> str:
        """إيقاف سيرفر THE WAY OUT الذي شغّله الإيجنت (تنظيف)."""
        proc = Tools.RUNNING_PROCESSES.pop("wayout", None)
        if proc is None or proc.poll() is not None:
            return "ℹ️ لا يوجد سيرفر شغال حالياً."
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        return "🛑 تم إيقاف سيرفر THE WAY OUT."


# ===========================================================================
# تعريف الأدوات للموديل (Ollama Tool Calling schema)
# ===========================================================================
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "execute_terminal",
            "description": "تنفيذ أمر تيرمينال في جهاز المستخدم (dir, echo, python ...). الأوامر التدميرية محظورة.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string", "description": "الأمر المراد تنفيذه"}},
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "كتابة أو إنشاء أو تعديل ملف في الجهاز.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "مسار الملف"},
                    "content": {"type": "string", "description": "محتوى الملف كاملاً"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "قراءة ملف من الجهاز.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "مسار الملف"}},
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "عرض محتويات مجلد.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string", "description": "مسار المجلد (افتراضي: .)"}},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "launch_the_way_out",
            "description": "تشغيل مشروع THE WAY OUT محلياً على منفذ (افتراضي 5000). ينشئ سيرفر تجريبي لو الملف غير موجود.",
            "parameters": {
                "type": "object",
                "properties": {
                    "entry_file": {"type": "string", "description": "ملف التشغيل (افتراضي: app.py)"},
                    "port": {"type": "integer", "description": "المنفذ (افتراضي: 5000)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_website",
            "description": "قراءة وتصفح أي موقع على الإنترنت واستخراج نصه.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "رابط الموقع"}},
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_port",
            "description": "فحص هل منفذ/خدمة على الجهاز شغالة أم لا.",
            "parameters": {
                "type": "object",
                "properties": {
                    "port": {"type": "integer", "description": "رقم المنفذ"},
                    "host": {"type": "string", "description": "المضيف (افتراضي: localhost)"},
                },
                "required": ["port"],
            },
        },
    },
]


# ===========================================================================
# عقل الإيجنت (Ollama)
# ===========================================================================
class AgentBrain:
    def __init__(self, model: str = OLLAMA_MODEL, base_url: str = OLLAMA_BASE_URL):
        self.model = model
        self.base_url = base_url.rstrip("/")

    def check_connection(self) -> tuple[bool, str]:
        """فحص الاتصال بسيرفر Ollama ووجود الموديل."""
        try:
            with urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            models = [m.get("name", "") for m in data.get("models", [])]
            if any(self.model in m for m in models):
                return True, f"متصل — الموديل `{self.model}` جاهز. ✅"
            if models:
                return False, f"متصل لكن الموديل `{self.model}` غير موجود. المتاح: {models}"
            return False, "متصل لكن لا توجد موديلات — نفّذ: ollama run qwen2.5-coder:1.5b"
        except Exception as e:  # noqa: BLE001
            return False, f"تعذّر الاتصال بـ Ollama على {self.base_url} — {e}"

    def query(self, messages: list) -> dict:
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": TOOLS_SCHEMA,
            "stream": False,
            "options": {"temperature": 0.1},
        }
        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("message", {"role": "assistant", "content": ""})
        except Exception as e:  # noqa: BLE001
            return {
                "role": "assistant",
                "content": (
                    f"❌ خطأ في الاتصال بالموديل: {e}\n"
                    f"تأكد أن Ollama شغال وأن الموديل `{self.model}` موجود "
                    f"(جرّب: ollama run {self.model})."
                ),
            }


# ===========================================================================
# حلقة التنفيذ
# ===========================================================================
def _parse_tool_args(raw_args) -> dict:
    """Ollama أحياناً يرجع الـ arguments كنص JSON — وحّدها إلى dict."""
    if isinstance(raw_args, dict):
        return raw_args
    if isinstance(raw_args, str):
        try:
            parsed = json.loads(raw_args)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def run_agent(user_query: str, brain: AgentBrain, max_steps: int = AGENT_MAX_STEPS) -> None:
    messages: list = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_query},
    ]

    print(f"\n{Fore.CYAN}🧠 الإيجنت بيفكر ويخطط...{Style.RESET_ALL}")

    for step in range(1, max_steps + 1):
        msg = brain.query(messages)
        content = msg.get("content", "") or ""
        tool_calls = msg.get("tool_calls", []) or []

        if content.strip():
            print(f"{Fore.YELLOW}💭 الإيجنت: {content}{Style.RESET_ALL}")

        if not tool_calls:
            print(f"\n{Fore.GREEN}🎯 النتيجة:\n{content or '(لا يوجد رد نصي)'}{Style.RESET_ALL}\n")
            break

        messages.append(msg)

        for tool in tool_calls:
            fn = tool.get("function", {})
            fn_name = fn.get("name", "")
            args = _parse_tool_args(fn.get("arguments", {}))
            print(f"{Fore.BLUE}⚙️ [تنفيذ {step}/{max_steps}]: {fn_name}({args}){Style.RESET_ALL}")

            tool_fn = getattr(Tools, fn_name, None)
            if tool_fn is None:
                result = f"❌ الأداة `{fn_name}` غير موجودة."
            else:
                try:
                    result = tool_fn(**args)
                except TypeError as e:
                    result = f"❌ خطأ في باراميترات `{fn_name}`: {e}"
                except Exception as e:  # noqa: BLE001
                    result = f"❌ فشل تنفيذ `{fn_name}`: {e}"

            print(f"{Fore.MAGENTA}   ↳ الناتج: {str(result)[:250]}{Style.RESET_ALL}")

            messages.append({"role": "tool", "name": fn_name, "content": str(result)})
    else:
        print(f"\n{Fore.YELLOW}⚠️ وصلت لأقصى عدد خطوات ({max_steps}) — جرّب تقسيم طلبك لأجزاء أصغر.{Style.RESET_ALL}\n")


# ===========================================================================
# الفحص الذاتي (بدون موديل) — python agent.py --check
# ===========================================================================
def self_check() -> int:
    """يختبر كل الأدوات محلياً بدون الحاجة لـ Ollama. يرجع 0 عند النجاح."""
    import tempfile

    print(f"{Fore.CYAN}🔍 الفحص الذاتي للأدوات (بدون موديل)...{Style.RESET_ALL}\n")
    passed, failed, skipped = 0, 0, 0

    def report(name: str, ok: bool | None, detail: str = ""):
        nonlocal passed, failed, skipped
        detail = f" — {detail[:120]}" if detail else ""
        if ok is None:
            skipped += 1
            print(f"{Fore.YELLOW}⏭️  SKIP  {name}{detail}{Style.RESET_ALL}")
        elif ok:
            passed += 1
            print(f"{Fore.GREEN}✅ PASS  {name}{detail}{Style.RESET_ALL}")
        else:
            failed += 1
            print(f"{Fore.RED}❌ FAIL  {name}{detail}{Style.RESET_ALL}")

    # 1) كتابة + قراءة ملف
    with tempfile.TemporaryDirectory() as tmp:
        p = str(Path(tmp) / "selfcheck.txt")
        r1 = Tools.write_file(p, "مرحبا من الفحص الذاتي 👋")
        r2 = Tools.read_file(p)
        report("write_file + read_file", "تم إنشاء" in r1 and "مرحبا" in r2, r2[:60])
        r3 = Tools.list_files(tmp)
        report("list_files", "selfcheck.txt" in r3)
        r4 = Tools.read_file(str(Path(tmp) / "nope.txt"))
        report("read_file لملف غير موجود", "غير موجود" in r4)

    # 2) فلتر الأمان
    r5 = Tools.execute_terminal("echo hello-check")
    report("execute_terminal (أمر آمن)", "hello-check" in r5, r5[:60])
    r6 = Tools.execute_terminal("rm -rf / --no-preserve-root")
    report("execute_terminal (حظر أمر تدميري)", "محظور" in r6, r6[:80])

    # 3) المنافذ
    r7 = Tools.check_port(9)  # منفذ discard — غالباً مغلق
    report("check_port (منفذ مغلق)", "مغلق" in r7 or "مفتوح" in r7, r7[:80])

    # 4) تشغيل السيرفر التجريبي على منفذ مؤقت ثم إيقافه
    with tempfile.TemporaryDirectory() as tmp:
        entry = str(Path(tmp) / "demo_app.py")
        # منفذ حر مؤقت
        s = socket.socket()
        s.bind(("127.0.0.1", 0))
        free_port = s.getsockname()[1]
        s.close()
        r8 = Tools.launch_the_way_out(entry_file=entry, port=free_port)
        ok_server = f"localhost:{free_port}" in r8 or "تم تشغيل" in r8
        report("launch_the_way_out", ok_server, r8[:100])
        r9 = Tools.check_port(free_port)
        report("check_port (السيرفر شغال)", "مفتوح" in r9, r9[:80])
        Tools.stop_server()

    # 5) تصفح الويب (يتطلب إنترنت — يُتخطى عند غيابه)
    r10 = Tools.read_website("https://example.com")
    if "فشل فتح الرابط" in r10 or "فشل" in r10:
        report("read_website (يحتاج إنترنت)", None, r10[:100])
    else:
        report("read_website", "Example" in r10 or "محتوى الموقع" in r10, r10[:100])

    # 6) الاتصال بـ Ollama (اختياري في الفحص)
    brain = AgentBrain()
    ok, detail = brain.check_connection()
    report("Ollama connection (اختياري)", True if ok else None, detail[:120])

    print(
        f"\n{Fore.CYAN}النتيجة: {passed} ناجح ✅ | {failed} فاشل ❌ | {skipped} متخطى ⏭️{Style.RESET_ALL}"
    )
    return 0 if failed == 0 else 1


# ===========================================================================
# الواجهة الرئيسية
# ===========================================================================
BANNER = """
╔══════════════════════════════════════════════════════════╗
║        🚀  T H E   W A Y   O U T   A G E N T             ║
║                 جاهز للعمل على لابتوبك!                  ║
╚══════════════════════════════════════════════════════════╝
"""

HELP_TEXT = """أوامر سريعة:
  • اكتب طلبك بالعربي مباشرة (مثال: شغّل مشروع THE WAY OUT)
  • help / مساعدة  → عرض هذه الرسالة
  • exit / quit / خروج → إنهاء
"""


def interactive_loop(brain: AgentBrain) -> None:
    print(Fore.GREEN + BANNER + Style.RESET_ALL)
    ok, detail = brain.check_connection()
    color = Fore.GREEN if ok else Fore.RED
    print(f"{color}🔌 Ollama: {detail}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}💡 اكتب 'help' للمساعدة — 'exit' للخروج{Style.RESET_ALL}\n")

    while True:
        try:
            q = input(f"{Fore.CYAN}THE WAY OUT ❯ {Style.RESET_ALL}").strip()
        except (KeyboardInterrupt, EOFError):
            print(f"\n{Fore.YELLOW}👋 مع السلامة!{Style.RESET_ALL}")
            break
        if not q:
            continue
        if q.lower() in ("exit", "quit", "خروج"):
            print(f"{Fore.YELLOW}👋 مع السلامة!{Style.RESET_ALL}")
            break
        if q.lower() in ("help", "مساعدة", "?"):
            print(HELP_TEXT)
            continue
        run_agent(q, brain)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="THE WAY OUT Agent — مساعد ذكي محلي عبر Ollama",
        prog="agent.py",
    )
    parser.add_argument("--once", metavar="QUERY", help="تنفيذ أمر واحد ثم الخروج")
    parser.add_argument("--check", action="store_true", help="فحص ذاتي للأدوات بدون موديل")
    parser.add_argument("--version", action="store_true", help="عرض رقم النسخة")
    parser.add_argument("--model", default=OLLAMA_MODEL, help=f"اسم الموديل (افتراضي: {OLLAMA_MODEL})")
    parser.add_argument("--base-url", default=OLLAMA_BASE_URL, help="عنوان Ollama")
    parser.add_argument("--max-steps", type=int, default=AGENT_MAX_STEPS, help="أقصى خطوات لكل أمر")
    args = parser.parse_args(argv)

    if args.version:
        print(f"THE WAY OUT Agent v{__version__} (model: {args.model})")
        return 0

    if args.check:
        return self_check()

    brain = AgentBrain(model=args.model, base_url=args.base_url)

    if args.once:
        run_agent(args.once, brain, max_steps=args.max_steps)
        return 0

    interactive_loop(brain)
    Tools.stop_server()  # تنظيف السيرفر عند الخروج
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
