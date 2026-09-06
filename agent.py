#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 THE WAY OUT Agent v2.0 — Master Build (Arena.ai Master Prompt compliant)
=============================================================================
مهندس برمجي ذاتي التشغيل يعمل محلياً بالكامل عبر Ollama.

التشغيل (Windows PowerShell):
    cd the_way_out
    pip install -r requirements.txt   # أول مرة فقط
    python agent.py                   # وضع تفاعلي (كل الأدوات)
    python agent.py --toolset core    # وضع خفيف (7 أدوات — للموديلات الصغيرة)
    python agent.py --once "اعمل مشروع Flask"     # أمر واحد
    python agent.py --check           # فحص ذاتي بدون موديل
    python agent.py --list-tools      # عرض كل الأدوات

الإعداد عبر .env (انظر .env.example):
    OLLAMA_BASE_URL / OLLAMA_MODEL / OLLAMA_NUM_CTX
    AGENT_MAX_STEPS / AGENT_TIMEOUT / AGENT_TOOLSET / DEFAULT_PORT / MEMORY_FILE
"""

from __future__ import annotations

import argparse
import datetime
import difflib
import json
import os
import platform
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

__version__ = "2.9.0"

# ---------------------------------------------------------------------------
# تهيئة اختيارية: colorama + dotenv (الكود يعمل بدونهما)
# ---------------------------------------------------------------------------
try:
    from colorama import Fore, Style, init as _color_init

    _color_init(autoreset=True)
except Exception:  # pragma: no cover

    class _Dummy:
        def __getattr__(self, _name: str) -> str:
            return ""

    Fore = Style = _Dummy()  # type: ignore

try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except Exception:
    pass

# ---------------------------------------------------------------------------
# الإعدادات
# ---------------------------------------------------------------------------
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:1.5b")
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "8192"))
AGENT_MAX_STEPS = int(os.getenv("AGENT_MAX_STEPS", "8"))
AGENT_TIMEOUT = int(os.getenv("AGENT_TIMEOUT", "60"))
AGENT_TOOLSET = os.getenv("AGENT_TOOLSET", "full").strip().lower()
DEFAULT_PORT = int(os.getenv("DEFAULT_PORT", "5000"))
FRONTIER_API_KEY = os.getenv("FRONTIER_API_KEY", "").strip()
FRONTIER_BASE_URL = os.getenv("FRONTIER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
FRONTIER_MODEL = os.getenv("FRONTIER_MODEL", "qwen/qwen-2.5-coder-32b-instruct:free").strip()

# ===========================================================================
# 🧠 SYSTEM PROMPT — مطابِق للماستر برومبت (v10.0 ULTIMATE)
# ===========================================================================
SYSTEM_PROMPT = """أنت **THE WAY OUT Agent** — مهندس برمجيات ذاتي التشغيل بيشتغل محلياً على جهاز المستخدم.
شعارك: "دايماً في طريق للخروج من أي مشكلة." بتتكلم بالعربي المصري، محترف وودود وحاسم.

## قواعدك الأساسية (لا تخالفها أبداً):

### 1. التنفيذ الفعلي أولاً (Execution First)
- **ما تقولش "هعمل"** — نفّذ فوراً باستخدام الـ tools المتاحة.
- "اعمل ملف" → `write_file` مباشرة. "شغل المشروع" → `launch_project` مباشرة. "افحص الموقع" → `browse_web` مباشرة.
- استدعِ الأدوات عبر آلية function calling فقط — **ممنوع كتابة JSON كنص في ردك**. النصوص (مثل content) أرسلها خاماً بدون تغليف في كائنات.
- ⛔ ممنوع الادعاء بتنفيذ مهمة بدون استدعاء الأدوات فعلاً — أي رد نهائي لمهمة تنفيذية بدون أدوات = فشل. نفّذ أولاً ثم بلّغ.
- 🔁 ممنوع تكرار نفس الرد مرتين — لو ردّك السابق اترفض، غيّر سلوكك فوراً ونفّذ بالأدوات.
- نفّذ بافتراضات منطقية واذكرها، بدل ما تسأل أسئلة كتير.

### 2. القراءة قبل الكتابة (Read Before Write)
- قبل ما تعدّل أي ملف → `read_file` الأول. قبل ما تنشئ مشروع → `list_directory` لفحص المكان.
- افهم السياق قبل ما تتحرك.

### 3. التحقق بعد التنفيذ (Verify After Action)
- بعد تشغيل سيرفر → `check_health` للتأكد. بعد كتابة كود → `run_python` للاختبار.
- بعد تعديل ملف → اقرأه من جديد للتأكيد. لا تعلن النجاح قبل التحقق.

### 4. الإصلاح الذاتي (Self-Healing)
- لو حصل خطأ → اقرأ رسالته بالكامل وحلل السبب الجذري.
- جرّب حلاً بديلاً **مختلفاً** (مثال: ModuleNotFoundError → ثبّت المكتبة بـ `install_package` ثم أعد التشغيل).
- ممنوع تكرار نفس الاستدعاء الفاشل أكثر من 3 مرات — لو فشلت 3 مرات اسأل المستخدم بوضوح.

### 5. الذاكرة والتعلم (Memory & Learning)
- احفظ تفضيلات المستخدم وقرارات المشروع بـ `remember`.
- قبل المهام المرتبطة بالماضي استرجع بـ `recall`.
- سجّل الدروس من الأخطاء المتكررة.

### 6. التواصل المصري (Egyptian Communication)
- رد بالعربي المصري (مش الفصحى الجافة). مختصر وعملي.
- إيموجي مناسبة (🚀 ✅ ❌ 💡 🔧). تجنب الشرح الطويل غير الضروري.

### 7. الأمان (Security First)
- **ممنوع نهائياً** الأوامر التدميرية: `rm -rf /` ، `format c:` ، `del /f /s /q c:\\` ، `shutdown/reboot` بدون إذن صريح.
- **ممنوع** تخزين passwords أو API keys في الكود — استخدم `.env`.
- لا تحذف ملفات مهمة بدون تأكيد المستخدم.

## نمط التنفيذ (ReAct):
1. 💭 فكّر: افهم الطلب، ضع خطة خطوات، حدد الأدوات.
2. ⚙️ نفّذ: أول أداة ثم انتظر النتيجة.
3. 👀 لاحظ: اقرأ النتيجة، هل نجحت؟
4. 🎯 قرر: نجاح → الخطوة التالية أو الإجابة النهائية. خطأ → أصلح وأعد (max 3x). لو كل الخطوات اكتملت: اكتب التقرير النهائي فوراً (نص عربي بدون JSON) وتوقف عن الأدوات — ممنوع تكرار نفس الاستدعاء الناجح.
5. 📢 بلّغ: تقرير نهائي مختصر بالمصري: ✅ ما تم، 📊 النتائج، 💡 الخطوة الجاية (لو relevant).

## صيغة الرد:
- مهام بسيطة: سطر ✅ لما تم، ثم `📊 النتيجة`، ثم `💡 اقتراح اختياري`.
- مهام معقدة: 📋 الخطة → ⚙️ التنفيذ → 🎯 النتيجة النهائية → 📊 إحصائيات.
- أخطاء: ❌ الخطأ → 🔍 السبب → 🩹 محاولة الإصلاح → 💡 الحل المقترح.
- الرد النهائي مختصر (أقل من 300 كلمة إلا لو كود).

## عباراتك المفضلة:
"خلاص كده اتعمل ✅" ، "يلا نجرب الحل ده 💡" ، "كله تمام والشغل خلص 🚀" ، "في مشكلة صغيرة، هصلحها 🔧" ، "عايز أضيف حاجة تانية؟"

تذكّر: There's ALWAYS a way out. نفّذ، تحقق، ثم بلّغ. 🚀"""

FIRST_RUN_GREETING = """🚀 أهلاً وسهلاً! أنا **THE WAY OUT Agent**

مهندس برمجي ذاتي التشغيل بيشتغل على جهازك محلياً 💻

✨ ممكن أعمل ليك:
- 💻 مشاريع برمجية كاملة (Flask, FastAPI, static...)
- 🌐 تصفح المواقع والبحث وسحب البيانات
- 🔧 إصلاح الأكواد ومراجعتها وتحسين الأداء
- 📊 أتمتة المهام + ذاكرة دائمة بتفتكر تفضيلاتك
- 🧠 فريق وكلاء ومهارات متقدمة — اسألني!

💡 جرّب تقول:
- "اعمل مشروع Flask مع صفحة رئيسية"
- "شغل الملف app.py وقولي لو في مشاكل"
- "ابحث عن شرح FastAPI ولخص النتايج"
- "راجع الكود ده وقولي رأيك"

يلا نبدأ! ⚡"""


# ---------------------------------------------------------------------------
# 🌐 Frontier provider — موديلات قوية عبر API متوافق مع OpenAI (خطط مجانية)
# يدعم: OpenRouter (موديلات :free) / Groq (طبقة مجانية) / Gemini (حصة مجانية)
# ---------------------------------------------------------------------------
FRONTIER_SETUP_HELP = """💡 للإجابات الأقوى مجاناً (دقيقتين):
1) OpenRouter (الأسهل): اعمل حساب على https://openrouter.ai وانسخ مفتاحاً من Keys، ثم في .env:
   FRONTIER_API_KEY=sk-or-v1-xxx
   FRONTIER_MODEL=qwen/qwen-2.5-coder-32b-instruct:free
   (قائمة المجاني تتغير — راجع: openrouter.ai/models?q=free)
2) Groq (الأسرع): مفتاح مجاني من https://console.groq.com ثم:
   FRONTIER_BASE_URL=https://api.groq.com/openai/v1
   FRONTIER_MODEL=llama-3.3-70b-versatile
3) Gemini (حصة مجانية كبيرة): مفتاح من https://aistudio.google.com ثم:
   FRONTIER_BASE_URL=https://generativelanguage.googleapis.com/v1beta1/openai
   FRONTIER_MODEL=gemini-2.0-flash"""


def frontier_configured() -> bool:
    return bool(FRONTIER_API_KEY)


def frontier_chat(messages: list, model: str | None = None,
                  timeout: int = 120) -> tuple[bool, str]:
    """محادثة عبر مزود OpenAI-compatible. ترجع (نجاح, النص/الخطأ)."""
    if not FRONTIER_API_KEY:
        return False, "FRONTIER_API_KEY غير مضبوط في .env"
    mdl = (model or FRONTIER_MODEL or "").strip()
    if not mdl:
        return False, "FRONTIER_MODEL غير مضبوط في .env"
    payload = {"model": mdl, "messages": messages}
    req = urllib.request.Request(
        f"{FRONTIER_BASE_URL}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {FRONTIER_API_KEY}",
                 "HTTP-Referer": "https://github.com/mafouda909-max/THE-AGENT",
                 "X-Title": "THE WAY OUT Agent"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8", errors="ignore")[:300]
        except Exception:
            detail = ""
        hints = {401: "المفتاح غلط أو منتهي — راجع FRONTIER_API_KEY.",
                 402: "رصيد غير كافٍ — استخدم موديلاً مجانياً (...:free).",
                 404: f"الموديل `{mdl}` غير موجود على المزود.",
                 429: "تجاوزت الحد المجاني — انتظر دقيقة وحاول."}
        return False, f"خطأ {e.code}: {hints.get(e.code, detail or e.reason)}"
    except Exception as e:  # noqa: BLE001
        return False, f"فشل الاتصال بالمزود: {e}"
    choices = data.get("choices", [])
    if not choices:
        return False, f"رد فارغ من المزود: {str(data)[:300]}"
    content = (choices[0].get("message", {}).get("content", "") or "").strip()
    if not content:
        return False, "المزود رجع إجابة فارغة."
    return True, content


# ===========================================================================
# 🛠️ الأدوات (Tools) — مطابِقة للماستر برومبت
# ===========================================================================
class Tools:
    """كل أدوات الماستر برومبت — تنفيذ محلي حقيقي."""

    RUNNING_PROCESSES: dict = {}
    PROJECT_META: dict = {}

    BLOCKED_PATTERNS = [
        "rm -rf /", "rm -rf /*", "rm -rf ~", ":(){:|:&};:", "mkfs", "dd if=",
        "dd of=/dev/", "> /dev/sda", "format c:", "format d:",
        "del /f /s /q c:\\", "del /s /q c:\\windows", "rmdir /s /q c:\\windows",
        "rd /s /q c:\\windows", "remove-item c:\\* -recurse",
        "remove-item c:\\windows", "diskpart", "shutdown /s", "shutdown -h now",
        "shutdown -r", "reboot", "poweroff", "halt", "init 0", "init 6",
        "chmod -r 777 /", "chown -r ", "takeown /f c:\\windows",
    ]

    MAX_OUTPUT = 4000
    MAX_FILE_READ = 3000
    SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules",
                 ".pytest_cache", ".mypy_cache", "dist", "build"}

    # -- helpers ----------------------------------------------------------
    @staticmethod
    def _is_blocked(command: str) -> str | None:
        lowered = (command or "").lower()
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

    @staticmethod
    def _http_get(url: str, timeout: int = 15) -> tuple[str, str]:
        """يرجع (html, final_url). يرفع استثناء عند الفشل."""
        url = url.strip()
        if not re.match(r"^https?://", url, re.IGNORECASE):
            url = "http://" + url
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
            charset = resp.headers.get_content_charset() or "utf-8"
            return raw.decode(charset, errors="ignore"), resp.geturl()

    @staticmethod
    def _html_to_text(html: str) -> str:
        try:
            from bs4 import BeautifulSoup  # type: ignore

            soup = BeautifulSoup(html, "html.parser")
            for tag in soup(["script", "style", "noscript"]):
                tag.decompose()
            return soup.get_text(separator=" ", strip=True)
        except ImportError:
            text = re.sub(r"<script.*?</script>", " ", html, flags=re.S | re.I)
            text = re.sub(r"<style.*?</style>", " ", text, flags=re.S | re.I)
            text = re.sub(r"<[^<]+?>", " ", text)
            return " ".join(text.split())

    @staticmethod
    def _extract_code(text: str) -> str:
        m = re.search(r"```(?:\w+)?\s*\n(.*?)```", text, flags=re.S)
        if m:
            return m.group(1).strip()
        return text.strip()

    # .......................... 📁 File Operations ........................
    @staticmethod
    def write_file(path: str, content: str) -> str:
        """إنشاء أو تعديل ملف (ينشئ المجلدات تلقائياً)."""
        try:
            p = Path(path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            return f"✅ تم إنشاء وحفظ الملف: `{path}`"
        except Exception as e:  # noqa: BLE001
            return f"❌ فشل حفظ الملف `{path}`: {e}"

    @staticmethod
    def read_file(path: str) -> str:
        """قراءة محتوى ملف (أول 3000 حرف)."""
        p = Path(path)
        if not p.exists():
            return f"❌ الملف `{path}` غير موجود."
        if p.is_dir():
            return f"ℹ️ `{path}` مجلد وليس ملفاً — استخدم list_directory لعرض محتوياته."
        try:
            return p.read_text(encoding="utf-8", errors="ignore")[: Tools.MAX_FILE_READ]
        except Exception as e:  # noqa: BLE001
            return f"❌ فشل قراءة الملف `{path}`: {e}"

    @staticmethod
    def edit_file(path: str, find: str, replace: str) -> str:
        """تعديل جزء محدد داخل ملف (أول تطابق فقط)."""
        p = Path(path)
        if not p.exists() or p.is_dir():
            return f"❌ الملف `{path}` غير موجود."
        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
            if find not in content:
                return (f"❌ النص المطلوب غير موجود في `{path}` — اقرأ الملف بـ read_file "
                        f"الأول وتأكد من النص حرفياً.")
            count = content.count(find)
            content = content.replace(find, replace, 1)
            p.write_text(content, encoding="utf-8")
            extra = f" (كان مكرراً {count} مرات — عدّلت الأول فقط)" if count > 1 else ""
            return f"✅ تم تعديل `{path}` بنجاح{extra}."
        except Exception as e:  # noqa: BLE001
            return f"❌ فشل تعديل الملف `{path}`: {e}"

    @staticmethod
    def list_directory(path: str = ".") -> str:
        """عرض محتويات مجلد."""
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
    def delete_file(path: str) -> str:
        """حذف ملف (تأكد من المستخدم قبل الملفات المهمة!)."""
        p = Path(path)
        if not p.exists():
            return f"❌ الملف `{path}` غير موجود أصلاً."
        if p.is_dir():
            return f"⛔ `{path}` مجلد — الحذف مقصور على الملفات فقط (أمان)."
        try:
            p.unlink()
            return f"🗑️ تم حذف الملف `{path}`."
        except Exception as e:  # noqa: BLE001
            return f"❌ فشل حذف الملف `{path}`: {e}"

    @staticmethod
    def search_files(pattern: str, directory: str = ".") -> str:
        """بحث بنمط (regex أو نص) داخل ملفات مجلد."""
        root = Path(directory)
        if not root.is_dir():
            return f"❌ المجلد `{directory}` غير موجود."
        try:
            rx = re.compile(pattern, re.IGNORECASE)
        except re.error:
            rx = re.compile(re.escape(pattern), re.IGNORECASE)
        matches: list[str] = []
        scanned = 0
        try:
            for f in root.rglob("*"):
                if len(matches) >= 50 or scanned >= 500:
                    break
                if not f.is_file() or f.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif",
                        ".ico", ".pdf", ".zip", ".exe", ".dll", ".pyc", ".mp3", ".mp4"}:
                    continue
                if any(part in Tools.SKIP_DIRS for part in f.parts):
                    continue
                try:
                    if f.stat().st_size > 500_000:
                        continue
                except OSError:
                    continue
                scanned += 1
                try:
                    text = f.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                for i, line in enumerate(text.splitlines(), 1):
                    if rx.search(line):
                        matches.append(f"{f}:{i}: {line.strip()[:150]}")
                        if len(matches) >= 50:
                            break
            if not matches:
                return f"🔍 لا توجد نتائج للنمط `{pattern}` في `{directory}` (فُحص {scanned} ملف)."
            more = f"\n… (عُرض أول 50 نتيجة)" if len(matches) >= 50 else ""
            return f"🔍 نتائج `{pattern}` ({len(matches)} — فُحص {scanned} ملف):\n" + "\n".join(matches) + more
        except Exception as e:  # noqa: BLE001
            return f"❌ فشل البحث: {e}"

    # .......................... 💻 System Operations ......................
    @staticmethod
    def execute_terminal(command: str) -> str:
        """تنفيذ أمر ترمينال (الأوامر التدميرية محظورة)."""
        blocked = Tools._is_blocked(command)
        if blocked:
            return f"⛔ أمر محظور لأسباب أمنية (تطابق مع: `{blocked}`) — لن يُنفَّذ."
        try:
            res = subprocess.run(command, shell=True, capture_output=True,
                                 text=True, timeout=AGENT_TIMEOUT)
            out = res.stdout.strip() or res.stderr.strip() or "(تم التنفيذ بدون مخرجات)"
            if res.returncode != 0:
                out = f"⚠️ خرج الكود {res.returncode}:\n{out}"
            return Tools._truncate(out, Tools.MAX_OUTPUT)
        except subprocess.TimeoutExpired:
            return f"⏱️ انتهت المهلة ({AGENT_TIMEOUT}s) قبل اكتمال الأمر."
        except Exception as e:  # noqa: BLE001
            return f"❌ فشل التنفيذ: {e}"

    @staticmethod
    def run_python(code_or_file: str) -> str:
        """تشغيل كود بايثون أو ملف .py واختباره."""
        target = (code_or_file or "").strip()
        if not target:
            return "❌ لم يتم تمرير كود أو ملف."
        blocked = Tools._is_blocked(target)
        if blocked:
            return f"⛔ كود محظور لأسباب أمنية (تطابق مع: `{blocked}`) — لن يُنفَّذ."
        try:
            if Path(target).is_file():
                if not target.endswith(".py"):
                    return f"ℹ️ `{target}` ليس ملف بايثون — استخدم read_file لقراءته."
                cmd = [sys.executable, target]
            elif target.endswith(".py") and "\n" not in target and len(target) < 260:
                return f"❌ الملف `{target}` غير موجود — تحقق بالـ list_directory الأول."
            else:
                cmd = [sys.executable, "-c", target]
            env = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=AGENT_TIMEOUT, env=env)
            out = (res.stdout.strip() + ("\n" + res.stderr.strip() if res.stderr.strip() else "")).strip()
            out = out or "(اشتغل بدون مخرجات)"
            if res.returncode != 0:
                return f"❌ الكود فشل (خرج {res.returncode}):\n{Tools._truncate(out, Tools.MAX_OUTPUT)}"
            return f"✅ الكود اشتغل بنجاح:\n{Tools._truncate(out, Tools.MAX_OUTPUT)}"
        except subprocess.TimeoutExpired:
            return f"⏱️ انتهت المهلة ({AGENT_TIMEOUT}s) قبل اكتمال الكود."
        except Exception as e:  # noqa: BLE001
            return f"❌ فشل التشغيل: {e}"

    @staticmethod
    def install_package(package_name: str) -> str:
        """تثبيت مكتبة عبر pip (مثال: flask أو: requests beautifulsoup4)."""
        name = (package_name or "").strip()
        if not name:
            return "❌ لم يتم تمرير اسم مكتبة."
        if re.search(r"[;&|`$<>\n]", name):
            return "⛔ اسم المكتبة يحتوي رموزاً ممنوعة — لن يُنفَّذ (أمان)."
        pkgs = name.split()
        try:
            res = subprocess.run([sys.executable, "-m", "pip", "install", *pkgs],
                                 capture_output=True, text=True, timeout=300)
            tail = (res.stdout.strip() + "\n" + res.stderr.strip()).strip().splitlines()
            tail = "\n".join(tail[-8:])
            if res.returncode != 0:
                return f"❌ فشل تثبيت `{name}`:\n{tail[:1500]}"
            return f"✅ تم تثبيت `{name}` بنجاح.\n{tail[:800]}"
        except subprocess.TimeoutExpired:
            return "⏱️ انتهت المهلة (5 دقائق) أثناء التثبيت."
        except Exception as e:  # noqa: BLE001
            return f"❌ فشل التثبيت: {e}"

    @staticmethod
    def check_system() -> str:
        """فحص النظام: CPU و RAM والقرص والبايثون."""
        lines = ["🖥️ حالة النظام:"]
        lines.append(f"- OS: {platform.system()} {platform.release()} ({platform.machine()})")
        lines.append(f"- Python: {platform.python_version()}")
        lines.append(f"- CPU cores: {os.cpu_count()}")
        try:
            total, used, free = shutil.disk_usage(".")
            lines.append(f"- Disk: {free // (1024**3)}GB حر من {total // (1024**3)}GB")
        except Exception:
            pass
        try:
            import psutil  # type: ignore

            mem = psutil.virtual_memory()
            lines.append(f"- RAM: {mem.available // (1024**2)}MB متاح من {mem.total // (1024**2)}MB ({mem.percent}% مستخدم)")
            lines.append(f"- CPU usage: {psutil.cpu_percent(interval=0.5)}%")
        except ImportError:
            lines.append("- RAM: (ثبّت psutil لتفاصيل الذاكرة: install_package(\"psutil\"))")
        except Exception:
            pass
        lines.append(f"- Ollama: {OLLAMA_BASE_URL} | الموديل: {OLLAMA_MODEL}")
        return "\n".join(lines)

    # .......................... 🚀 Project Management .....................
    @staticmethod
    def create_project(name: str, template: str = "basic") -> str:
        """إنشاء مشروع جديد من قالب: basic / flask / fastapi / static."""
        template = (template or "basic").strip().lower()
        dest = Path(name)
        if dest.exists() and any(dest.iterdir()):
            return f"❌ المجلد `{name}` موجود وغير فارغ — اختر اسماً آخر أو احذفه أولاً."

        basic_app = 'print("Hello from THE WAY OUT project!")\n'
        flask_app = ('from flask import Flask\napp = Flask(__name__)\n\n'
                     '@app.route("/")\ndef home():\n    return "<h1>🚀 Flask is running!</h1>"\n\n'
                     'if __name__ == "__main__":\n    app.run(port=5000, debug=True)\n')
        fastapi_app = ('from fastapi import FastAPI\napp = FastAPI(title="THE WAY OUT API")\n\n'
                       '@app.get("/")\ndef home():\n    return {"status": "🚀 FastAPI is running!"}\n')
        static_html = ('<!DOCTYPE html><html lang="ar" dir="rtl"><head><meta charset="utf-8">'
                       '<title>THE WAY OUT</title></head><body>'
                       '<h1>🚀 المشروع شغال!</h1></body></html>\n')
        readme = f"# {name}\n\nتم إنشاؤه بواسطة 🚀 THE WAY OUT Agent (قالب: {template}).\n"
        gitignore = "__pycache__/\n.venv/\n.env\n*.log\n"

        templates = {
            "basic": {"app.py": basic_app, "requirements.txt": "",
                      "README.md": readme, ".gitignore": gitignore},
            "flask": {"app.py": flask_app, "requirements.txt": "flask\n",
                      "README.md": readme, ".gitignore": gitignore},
            "fastapi": {"main.py": fastapi_app, "requirements.txt": "fastapi\nuvicorn\n",
                        "README.md": readme, ".gitignore": gitignore},
            "static": {"index.html": static_html, "README.md": readme},
        }
        note = ""
        if template not in templates:
            # تسامح مع الموديلات الصغيرة: تستخرج اسم القالب من نص مشوش مثل "basic/flask/fastapi/static"
            found = [k for k in templates if k in template]
            if not found:
                return f"❌ القالب `{template}` غير معروف — المتاح: {', '.join(templates)}."
            note = f" (فسّرت `{template}` كـ `{found[0]}`)"
            template = found[0]
        try:
            for rel, content in templates[template].items():
                Tools.write_file(str(dest / rel), content)
            files = ", ".join(templates[template].keys())
            nxt = {"basic": 'run_python("NAME/app.py")', "flask": 'ثبّت flask ثم launch_project("NAME/app.py")',
                   "fastapi": 'ثبّت fastapi و uvicorn ثم شغل: uvicorn main:app',
                   "static": 'launch_project("NAME/index.html") — أو افتح الملف في المتصفح'}.get(template, "")
            return (f"✅ تم إنشاء المشروع `{name}` (قالب {template}){note} — الملفات: {files}\n"
                    f"💡 الخطوة الجاية: {nxt}".replace("NAME", name))
        except Exception as e:  # noqa: BLE001
            return f"❌ فشل إنشاء المشروع: {e}"

    _DEMO_SERVER_TEMPLATE = '''"""THE WAY OUT — demo server (auto-generated by agent)."""
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = __PORT__

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/html; charset=utf-8")
        self.end_headers()
        body = ("<h1>🚀 THE WAY OUT Project is Running Locally!</h1>"
                "<p>Agent is working perfectly on port __PORT__.</p>")
        self.wfile.write(body.encode("utf-8"))

if __name__ == "__main__":
    print("Server starting on port __PORT__...", flush=True)
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
'''

    @staticmethod
    def launch_project(entry_file: str = "app.py", port: int = 5000,
                       name: str = "wayout") -> str:
        """تشغيل مشروع محلياً (ينشئ سيرفر تجريبي لو الملف غير موجود)."""
        try:
            port = int(port)
        except (TypeError, ValueError):
            port = DEFAULT_PORT
        name = (name or "wayout").strip() or "wayout"

        Tools.stop_project(name)  # أوقف أي نسخة سابقة بنفس الاسم

        if not Path(entry_file).exists():
            demo = Tools._DEMO_SERVER_TEMPLATE.replace("__PORT__", str(port))
            Tools.write_file(entry_file, demo)

        logs_dir = Path("logs")
        logs_dir.mkdir(exist_ok=True)
        log_path = logs_dir / f"{name}.log"
        try:
            log_f = open(log_path, "w", encoding="utf-8")
            penv = {**os.environ, "PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8"}
            proc = subprocess.Popen([sys.executable, entry_file],
                                    stdout=log_f, stderr=subprocess.STDOUT,
                                    text=True, bufsize=1, env=penv)
        except Exception as e:  # noqa: BLE001
            return f"❌ فشل تشغيل `{entry_file}`: {e}"

        Tools.RUNNING_PROCESSES[name] = proc
        Tools.PROJECT_META[name] = {"port": port, "entry": entry_file,
                                    "pid": proc.pid, "log": str(log_path),
                                    "started": datetime.datetime.now().isoformat(timespec="seconds")}
        time.sleep(1.5)

        if proc.poll() is not None:
            code = proc.poll()
            err = Tools.read_logs(name, 15)
            if code == 0:
                return (f"ℹ️ الملف `{entry_file}` اشتغل وخلص فوراً (كود 0) — ده سكربت عادي مش سيرفر دائم، "
                        f"فعشان كده مفيش حاجة على المنفذ {port}. الناتج:\n{err}\n"
                        "💡 لو عايز سيرفر دائم: استخدم قالب static/flask/fastapi أو ملف فيه serve_forever.")
            return f"❌ السيرفر توقف فور تشغيله (كود {code}). آخر اللوجات:\n{err}"
        status = Tools.check_health(port)
        if "مفتوح" in status:
            return (f"🚀 تم تشغيل المشروع `{name}` بنجاح على http://localhost:{port}\n"
                    f"📝 اللوجات: {log_path}")
        return (f"⚠️ تم إطلاق العملية (PID={proc.pid}) لكن المنفذ {port} لا يستجيب بعد. "
                f"جرّب: check_health({port}) أو read_logs(\"{name}\").")

    @staticmethod
    def stop_project(name: str = "wayout") -> str:
        """إيقاف مشروع شغّله الإيجنت."""
        proc = Tools.RUNNING_PROCESSES.pop(name, None)
        Tools.PROJECT_META.pop(name, None)
        if proc is None or proc.poll() is not None:
            return f"ℹ️ لا يوجد مشروع شغال باسم `{name}`."
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        return f"🛑 تم إيقاف المشروع `{name}`."

    @staticmethod
    def check_health(port: int, host: str = "localhost") -> str:
        """فحص هل منفذ/سيرفر شغال أم لا."""
        try:
            with socket.create_connection((host, int(port)), timeout=3):
                return f"🟢 المنفذ {port} على {host} **مفتوح** — الخدمة شغالة. ✅"
        except (OSError, ValueError, OverflowError) as e:
            return f"🔴 المنفذ {port} على {host} **مغلق/لا يستجيب** ({e})."
        except Exception as e:  # noqa: BLE001
            return f"❌ تعذّر فحص المنفذ {port}: {e}"

    @staticmethod
    def read_logs(project: str = "wayout", lines: int = 50) -> str:
        """قراءة آخر سطور من لوجات مشروع."""
        meta = Tools.PROJECT_META.get(project, {})
        log_path = meta.get("log", str(Path("logs") / f"{project}.log"))
        p = Path(log_path)
        if not p.exists():
            return f"ℹ️ لا توجد لوجات للمشروع `{project}` ({log_path})."
        try:
            all_lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
            tail = all_lines[-int(lines):]
            return f"📝 آخر {len(tail)} سطر من لوجات `{project}`:\n" + ("\n".join(tail) or "(فارغ)")
        except Exception as e:  # noqa: BLE001
            return f"❌ فشل قراءة اللوجات: {e}"

    @staticmethod
    def monitor_project(name: str = "wayout") -> str:
        """مراقبة مشروع: هل شغال؟ المنفذ؟ آخر اللوجات؟"""
        proc = Tools.RUNNING_PROCESSES.get(name)
        meta = Tools.PROJECT_META.get(name, {})
        if proc is None:
            return f"ℹ️ المشروع `{name}` غير مسجّل كمشروع شغال. شغّله بـ launch_project أولاً."
        alive = proc.poll() is None
        out = [f"📊 مراقبة `{name}`:",
               f"- الحالة: {'🟢 شغال (PID=' + str(proc.pid) + ')' if alive else '🔴 متوقف (خرج بالكود ' + str(proc.poll()) + ')'}"]
        if meta.get("port"):
            out.append(f"- المنفذ {meta['port']}: {Tools.check_health(meta['port'])}")
        if meta.get("started"):
            out.append(f"- بدأ في: {meta['started']}")
        out.append(Tools.read_logs(name, 5))
        return "\n".join(out)

    # .......................... 🌐 Web & Internet ........................
    @staticmethod
    def browse_web(url: str) -> str:
        """قراءة محتوى موقع واستخراج نصه."""
        try:
            html, final_url = Tools._http_get(url)
            title = ""
            try:
                from bs4 import BeautifulSoup  # type: ignore

                soup = BeautifulSoup(html, "html.parser")
                title = (soup.title.string.strip() if soup.title and soup.title.string else "")
            except ImportError:
                m = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
                title = re.sub(r"\s+", " ", m.group(1)).strip() if m else ""
            clean = " ".join(Tools._html_to_text(html).split())
            if not clean:
                return "ℹ️ تم فتح الصفحة لكن لم يُستخرج نص (قد تكون صفحة JS تفاعلية)."
            head = f"📌 العنوان: {title}\n" if title else ""
            return f"📄 محتوى الموقع ({final_url}):\n{head}{clean[:2000]}"
        except Exception as e:  # noqa: BLE001
            return f"❌ فشل فتح الرابط {url}: {e}"

    @staticmethod
    def web_search(query: str, max_results: int = 8) -> str:
        """بحث على الإنترنت (DuckDuckGo — بدون API key)."""
        try:
            max_results = max(1, min(int(max_results), 15))
        except (TypeError, ValueError):
            max_results = 8
        try:
            q = urllib.parse.urlencode({"q": query})
            req = urllib.request.Request("https://html.duckduckgo.com/html/?" + q,
                                         headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="ignore")
            items = re.findall(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>'
                               r'.*?class="result__snippet"[^>]*>(.*?)</a>',
                               html, flags=re.S | re.I)
            if not items:  # محاولة بديلة أبسط
                items = [(m, t, "") for m, t in
                         re.findall(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
                                    html, flags=re.S | re.I)]
            if not items:
                return f"🔍 لا توجد نتائج لـ `{query}`."
            out = [f"🔍 نتائج البحث عن `{query}`:"]
            for i, (link, title, snippet) in enumerate(items[:max_results], 1):
                title = " ".join(re.sub(r"<[^>]+>", "", title).split())
                m = re.search(r"uddg=([^&]+)", link)
                if m:
                    link = urllib.parse.unquote(m.group(1))
                snippet = " ".join(re.sub(r"<[^>]+>", "", snippet).split())[:200]
                out.append(f"\n{i}. {title}\n   🔗 {link}" + (f"\n   {snippet}" if snippet else ""))
            return "\n".join(out)
        except Exception as e:  # noqa: BLE001
            return f"❌ فشل البحث (يحتاج إنترنت): {e}"

    @staticmethod
    def download_file(url: str, destination: str) -> str:
        """تنزيل ملف من رابط وحفظه (حد أقصى 50MB)."""
        try:
            req = urllib.request.Request(url.strip(), headers={"User-Agent": "Mozilla/5.0"})
            dest = Path(destination)
            dest.parent.mkdir(parents=True, exist_ok=True)
            size = 0
            with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as f:
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > 50 * 1024 * 1024:
                        f.close()
                        dest.unlink(missing_ok=True)
                        return "⛔ الملف أكبر من 50MB — تم إلغاء التنزيل (أمان)."
                    f.write(chunk)
            return f"✅ تم تنزيل `{url}` → `{destination}` ({size} بايت)."
        except Exception as e:  # noqa: BLE001
            return f"❌ فشل التنزيل: {e}"

    @staticmethod
    def call_api(url: str, method: str = "GET", headers: str = "",
                 body: str = "") -> str:
        """استدعاء API: GET/POST/PUT/DELETE مع headers و body اختياريين."""
        try:
            method = (method or "GET").upper()
            hdrs: dict = {}
            if headers:
                hdrs = json.loads(headers) if isinstance(headers, str) else dict(headers)
            data = None
            if body:
                if isinstance(body, dict):
                    data = json.dumps(body).encode("utf-8")
                    hdrs.setdefault("Content-Type", "application/json")
                else:
                    try:
                        json.loads(body)
                        data = body.encode("utf-8")
                        hdrs.setdefault("Content-Type", "application/json")
                    except (json.JSONDecodeError, TypeError):
                        data = str(body).encode("utf-8")
            req = urllib.request.Request(url.strip(), data=data, headers=hdrs, method=method)
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = resp.read().decode("utf-8", errors="ignore")
            return f"✅ HTTP {resp.status} من {url}:\n{Tools._truncate(payload, 2000)}"
        except Exception as e:  # noqa: BLE001
            return f"❌ فشل استدعاء الـ API: {e}"

    @staticmethod
    def scrape_data(url: str, selector: str = "") -> str:
        """سحب بيانات من موقع — مع CSS selector اختياري (يحتاج beautifulsoup4)."""
        try:
            html, final_url = Tools._http_get(url)
            if not selector:
                clean = " ".join(Tools._html_to_text(html).split())
                return f"📄 نص الصفحة ({final_url}):\n{clean[:3000]}"
            try:
                from bs4 import BeautifulSoup  # type: ignore
            except ImportError:
                return ("❌ الـ selector يحتاج مكتبة beautifulsoup4 — ثبّتها بـ "
                        "install_package(\"beautifulsoup4\") ثم أعد المحاولة.")
            soup = BeautifulSoup(html, "html.parser")
            els = soup.select(selector)
            if not els:
                return f"🔍 لا توجد عناصر مطابقة لـ `{selector}` في {final_url}."
            out = [f"🔍 سحب `{selector}` من {final_url} ({len(els)} عنصر):"]
            for el in els[:50]:
                out.append(f"- {el.get_text(separator=' ', strip=True)[:300]}")
            return Tools._truncate("\n".join(out), 3000)
        except Exception as e:  # noqa: BLE001
            return f"❌ فشل السحب: {e}"

    # .......................... 🧠 Memory & Learning ......................
    @staticmethod
    def _memory_path() -> Path:
        return Path(os.getenv("MEMORY_FILE", "memory.json"))

    @staticmethod
    def _load_mem() -> list:
        try:
            p = Tools._memory_path()
            if p.exists():
                data = json.loads(p.read_text(encoding="utf-8"))
                return data if isinstance(data, list) else []
        except Exception:
            pass
        return []

    @staticmethod
    def _save_mem(items: list) -> None:
        Tools._memory_path().write_text(json.dumps(items, ensure_ascii=False, indent=2),
                                        encoding="utf-8")

    @staticmethod
    def remember(fact: str, category: str = "general") -> str:
        """حفظ معلومة في الذاكرة الدائمة (تفضيلات المستخدم وقرارات المشروع)."""
        fact = (fact or "").strip()
        if not fact:
            return "❌ لا يمكن حفظ معلومة فارغة."
        items = Tools._load_mem()
        new_id = (max([m.get("id", 0) for m in items]) + 1) if items else 1
        items.append({"id": new_id, "fact": fact,
                      "category": (category or "general").strip() or "general",
                      "ts": datetime.datetime.now().isoformat(timespec="seconds")})
        try:
            Tools._save_mem(items)
            return f"🧠 تم الحفظ في الذاكرة (#{new_id} | {category}): {fact[:150]}"
        except Exception as e:  # noqa: BLE001
            return f"❌ فشل الحفظ: {e}"

    @staticmethod
    def recall(query: str) -> str:
        """استرجاع معلومات من الذاكرة حسب كلمات البحث."""
        words = [w for w in re.split(r"\W+", (query or "").lower()) if len(w) > 2]
        items = Tools._load_mem()
        if not items:
            return "🧠 الذاكرة فارغة — احفظ معلومات بـ remember أولاً."
        if not words:
            return "❌ اكتب كلمة بحث أوضح."
        scored = []
        for m in items:
            text = f"{m.get('fact', '')} {m.get('category', '')}".lower()
            score = sum(1 for w in words if w in text)
            if score:
                scored.append((score, m))
        if not scored:
            return f"🧠 لا توجد ذكريات مطابقة لـ `{query}`."
        scored.sort(key=lambda x: -x[0])
        out = [f"🧠 نتائج الاسترجاع لـ `{query}`:"]
        for _, m in scored[:5]:
            out.append(f"- #{m.get('id')} [{m.get('category')}] {m.get('fact')}")
        return "\n".join(out)

    @staticmethod
    def list_memories(category: str = "") -> str:
        """عرض كل الذاكرة (مع فلترة اختيارية بالتصنيف)."""
        items = Tools._load_mem()
        if category:
            items = [m for m in items if m.get("category") == category]
        if not items:
            return "🧠 لا توجد ذكريات" + (f" في تصنيف `{category}`." if category else ".")
        out = [f"🧠 الذاكرة ({len(items)} معلومة):"]
        for m in items[-30:]:
            out.append(f"- #{m.get('id')} [{m.get('category')}] {m.get('fact')}")
        return "\n".join(out)

    @staticmethod
    def forget(fact_id: int) -> str:
        """نسيان معلومة من الذاكرة برقمها."""
        try:
            fid = int(fact_id)
        except (TypeError, ValueError):
            return "❌ رقم المعلومة يجب أن يكون عدداً صحيحاً."
        items = Tools._load_mem()
        kept = [m for m in items if m.get("id") != fid]
        if len(kept) == len(items):
            return f"❌ لا توجد معلومة برقم #{fid}."
        try:
            Tools._save_mem(kept)
            return f"🧠 تم نسيان المعلومة #{fid}."
        except Exception as e:  # noqa: BLE001
            return f"❌ فشل الحذف: {e}"

    # .......................... 🔧 Code Assistance ........................
    @staticmethod
    def _code_context(path: str) -> tuple[str | None, str]:
        p = Path(path)
        if not p.exists() or p.is_dir():
            return None, f"❌ الملف `{path}` غير موجود."
        try:
            code = p.read_text(encoding="utf-8", errors="ignore")[:6000]
            return code, ""
        except Exception as e:  # noqa: BLE001
            return None, f"❌ فشل قراءة الملف: {e}"

    @staticmethod
    def _ask_brain(prompt: str, system: str = "") -> str:
        brain = get_brain()
        out = brain.chat_simple(prompt, system=system or None)
        if out is None:
            return ("❌ تعذّر الاتصال بالموديل — تأكد أن Ollama شغال "
                    f"والموديل `{brain.model}` موجود.")
        return out

    @staticmethod
    def analyze_code(file: str) -> str:
        """تحليل كود: البنية ونقاط القوة والمخاطر."""
        code, err = Tools._code_context(file)
        if code is None:
            return err
        return ("🔍 تحليل `{}`:\n".format(file) + Tools._ask_brain(
            f"حلّل الكود التالي باختصار بالعربي: البنية، نقاط القوة، المخاطر المحتملة.\n\n```\n{code}\n```",
            system="أنت محلل أكواد خبير. رد بالعربي المصري المختصر."))

    @staticmethod
    def review_code(file: str) -> str:
        """مراجعة كود: مشاكل + اقتراحات تحسين."""
        code, err = Tools._code_context(file)
        if code is None:
            return err
        return ("📝 مراجعة `{}`:\n".format(file) + Tools._ask_brain(
            f"راجع الكود التالي: اذكر المشاكل مرتبة بالأهمية ثم اقتراحات تحسين عملية. رد بالعربي.\n\n```\n{code}\n```",
            system="أنت مراجع أكواد صارم وعملي. رد بالعربي المصري المختصر."))

    @staticmethod
    def explain_code(file: str) -> str:
        """شرح كود بالعربي ببساطة."""
        code, err = Tools._code_context(file)
        if code is None:
            return err
        return ("💡 شرح `{}`:\n".format(file) + Tools._ask_brain(
            f"اشرح الكود التالي بالعربي المصري البسيط كأنك تشرح لمبتدئ: ماذا يفعل كل جزء؟\n\n```\n{code}\n```",
            system="أنت معلم برمجة صبور. اشرح بالعربي المصري البسيط."))

    @staticmethod
    def find_bugs(file: str) -> str:
        """البحث عن أخطاء محتملة في كود."""
        code, err = Tools._code_context(file)
        if code is None:
            return err
        return ("🐞 فحص الأخطاء في `{}`:\n".format(file) + Tools._ask_brain(
            f"ابحث عن الأخطاء المحتملة (bugs) في الكود التالي: اذكر كل خطأ مع السطر التقريبي وسببه وكيفية إصلاحه. رد بالعربي.\n\n```\n{code}\n```",
            system="أنت خبير اكتشاف أخطاء. رد بالعربي المصري المختصر."))

    @staticmethod
    def generate_tests(file: str) -> str:
        """توليد اختبارات pytest لملف وحفظها في tests/."""
        code, err = Tools._code_context(file)
        if code is None:
            return err
        out = Tools._ask_brain(
            "اكتب اختبارات pytest للكود التالي. أخرج كود الاختبارات فقط داخل ```python bloc"
            "k واحد بدون شرح.\n\n```\n" + code + "\n```",
            system="أنت خبير اختبارات. أخرج الكود فقط.")
        if out.startswith("❌"):
            return out
        tests_code = Tools._extract_code(out)
        stem = Path(file).stem
        dest = Path("tests") / f"test_{stem}_gen.py"
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            dest.write_text(tests_code, encoding="utf-8")
            return f"✅ تم توليد الاختبارات في `{dest}` — شغّلها بـ: pytest {dest}"
        except Exception as e:  # noqa: BLE001
            return f"❌ فشل حفظ الاختبارات: {e}"

    @staticmethod
    def refactor_code(file: str, goal: str = "تحسين الجودة") -> str:
        """إعادة هيكلة ملف حسب هدف (مع نسخة احتياطية .bak)."""
        code, err = Tools._code_context(file)
        if code is None:
            return err
        out = Tools._ask_brain(
            f"أعد هيكلة الكود التالي بهدف: {goal}. أخرج الملف الكامل الجديد فقط داخل ``` block واحد بدون شرح.\n\n```\n{code}\n```",
            system="أنت خبير إعادة هيكلة. أخرج الكود الكامل فقط.")
        if out.startswith("❌"):
            return out
        new_code = Tools._extract_code(out)
        try:
            Path(file).write_text(Path(file).read_text(encoding="utf-8", errors="ignore"),
                                  encoding="utf-8")  # تأكيد الصلاحية
            Path(str(file) + ".bak").write_text(code, encoding="utf-8")
            Path(file).write_text(new_code, encoding="utf-8")
            return f"✅ تمت إعادة هيكلة `{file}` (الهدف: {goal}). النسخة الأصلية محفوظة في `{file}.bak`."
        except Exception as e:  # noqa: BLE001
            return f"❌ فشل إعادة الهيكلة: {e}"

    # .......................... 🎨 Content Generation .....................
    @staticmethod
    def generate_readme(project: str = ".") -> str:
        """كتابة README احترافي لمشروع (لا يستبدل الموجود — ينشئ README.generated.md)."""
        root = Path(project)
        if not root.is_dir():
            return f"❌ المجلد `{project}` غير موجود."
        tree = []
        for f in sorted(root.rglob("*"))[:60]:
            if any(part in Tools.SKIP_DIRS or part.startswith(".git") for part in f.parts):
                continue
            try:
                rel = f.relative_to(root)
                tree.append(f"📁 {rel}/" if f.is_dir() else f"📄 {rel}")
            except ValueError:
                continue
        out = Tools._ask_brain(
            f"اكتب ملف README.md احترافي بالعربي مع عناوين إنجليزية للمشروع التالي. أخرج الماركداون فقط.\n\nهيكل المشروع:\n" + "\n".join(tree[:40]),
            system="أنت كاتب توثيق تقني محترف.")
        if out.startswith("❌"):
            return out
        content = Tools._extract_code(out)
        dest = root / ("README.generated.md" if (root / "README.md").exists() else "README.md")
        try:
            dest.write_text(content, encoding="utf-8")
            return f"✅ تم إنشاء `{dest}`."
        except Exception as e:  # noqa: BLE001
            return f"❌ فشل الحفظ: {e}"

    @staticmethod
    def generate_documentation(file: str) -> str:
        """توليد توثيق لملف كود وحفظه في docs/."""
        code, err = Tools._code_context(file)
        if code is None:
            return err
        out = Tools._ask_brain(
            "ولّد توثيقاً تقنياً بالعربي للكود التالي: نظرة عامة، الدوال/الأصناف، أمثلة استخدام. أخرج الماركداون فقط.\n\n```\n" + code + "\n```",
            system="أنت كاتب توثيق تقني محترف.")
        if out.startswith("❌"):
            return out
        dest = Path("docs") / f"{Path(file).stem}.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            dest.write_text(Tools._extract_code(out), encoding="utf-8")
            return f"✅ تم إنشاء التوثيق في `{dest}`."
        except Exception as e:  # noqa: BLE001
            return f"❌ فشل الحفظ: {e}"

    @staticmethod
    def generate_content(topic: str, type: str = "article") -> str:
        """إنشاء محتوى (article/post/script) وحفظه في content/."""
        topic = (topic or "").strip()
        if not topic:
            return "❌ حدد الموضوع."
        ctype = (type or "article").strip().lower()
        out = Tools._ask_brain(
            f"اكتب {ctype} بالعربي المصري الجذاب عن: {topic}. نسّقه بعناوين ونقاط.",
            system="أنت كاتب محتوى عربي محترف.")
        if out.startswith("❌"):
            return out
        slug = re.sub(r"\W+", "_", topic, flags=re.UNICODE).strip("_")[:40] or "content"
        dest = Path("content") / f"{slug}.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            dest.write_text(out, encoding="utf-8")
            return f"✅ تم إنشاء المحتوى في `{dest}`."
        except Exception as e:  # noqa: BLE001
            return f"❌ فشل الحفظ: {e}"

    # .......................... 📊 Monitoring & Automation ................
    @staticmethod
    def create_automation(trigger: str = "manual", action: str = "") -> str:
        """إنشاء أتمتة: trigger (manual/daily/hourly/startup) + action (أمر)."""
        trigger = (trigger or "manual").strip().lower()
        action = (action or "").strip()
        if not action:
            return "❌ حدد الأمر (action) المراد أتمتته."
        if Tools._is_blocked(action):
            return "⛔ الأمر يحتوي نمطاً تدميرياً — مرفوض (أمان)."
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        is_win = platform.system() == "Windows"
        script_name = f"scripts/auto_{ts}.{'ps1' if is_win else 'sh'}"
        script_body = (f"# Auto-generated by THE WAY OUT Agent — trigger: {trigger}\n{action}\n"
                       if is_win else f"#!/bin/sh\n# trigger: {trigger}\n{action}\n")
        try:
            Tools.write_file(script_name, script_body)
            reg_path = Path("automations.json")
            reg = json.loads(reg_path.read_text(encoding="utf-8")) if reg_path.exists() else []
            reg.append({"trigger": trigger, "action": action, "script": script_name, "ts": ts})
            reg_path.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")
            hint = (f'💡 للجدولة التلقائية: schedule_task("0 9 * * *", "{action}")'
                    if trigger in ("daily", "hourly") else
                    "💡 شغّل السكربت يدوياً أو اربطه بـ schedule_task للجدولة.")
            return f"✅ تم إنشاء الأتمتة `{script_name}` (trigger: {trigger}).\n{hint}"
        except Exception as e:  # noqa: BLE001
            return f"❌ فشل إنشاء الأتمتة: {e}"

    @staticmethod
    @staticmethod
    def _parse_schedule(spec: str) -> tuple[str | None, str]:
        """يحلّل HH:MM أو cron خماسياً. يرجع (cron خماسي, HH:MM) أو (None, '')."""
        spec = (spec or "").strip()
        m = re.fullmatch(r"(\d{1,2}):(\d{2})", spec)
        if m:
            h, mi = int(m.group(1)), int(m.group(2))
            if 0 <= h <= 23 and 0 <= mi <= 59:
                return f"{mi} {h} * * *", f"{h:02d}:{mi:02d}"
            return None, ""
        parts = spec.split()
        if len(parts) == 5 and all(re.fullmatch(r"[\d\*/,\-]+", p) for p in parts):
            hh_mm = "09:00"
            if parts[0].isdigit() and parts[1].isdigit():
                hh_mm = f"{int(parts[1]) % 24:02d}:{int(parts[0]) % 60:02d}"
            return spec, hh_mm
        return None, ""

    @staticmethod
    def schedule_task(cron: str = "0 9 * * *", command: str = "") -> str:
        """جدولة حقيقية: Windows عبر schtasks، وLinux/macOS عبر crontab (مع نسخة احتياطية). يقبل HH:MM أو cron."""
        command = (command or "").strip()
        if not command:
            return "❌ حدد الأمر (command) المراد جدولته."
        if Tools._is_blocked(command):
            return "⛔ الأمر يحتوي نمطاً تدميرياً — مرفوض (أمان)."

        fields, hh_mm = Tools._parse_schedule(cron or "")
        if fields is None:
            return ("❌ صيغة الوقت غير مفهومة — أمثلة صحيحة:\n"
                    '- "09:30" (يومياً الساعة 9:30 صباحاً)\n'
                    '- "0 9 * * *" (نفس الشيء بصيغة cron)\n'
                    '- "*/15 * * * *" (كل 15 دقيقة)')
        if fields == "* * * * *":
            return "⛔ الجدولة كل دقيقة مرفوضة (خطر إغراق النظام) — استخدم كل 5 دقائق على الأقل: `*/5 * * * *`."

        if os.getenv("SCHEDULE_DRY_RUN", "") == "1":
            line = f"{fields} {command}  # THE WAY OUT (dry-run)"
            try:
                with open("scheduled_tasks.txt", "a", encoding="utf-8") as f:
                    f.write(line + "\n")
                return (f"📝 وضع تجريبي (SCHEDULE_DRY_RUN=1) — لم يُثبَّت شيء.\n"
                        f"السطر الذي كان سيُثبَّت:\n{line}\nحُفظ في `scheduled_tasks.txt`.")
            except Exception as e:  # noqa: BLE001
                return f"❌ فشل الحفظ: {e}"

        if platform.system() == "Windows":
            task = "Wayout_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            try:
                res = subprocess.run(["schtasks", "/Create", "/SC", "DAILY", "/TN", task,
                                      "/TR", f"cmd /c {command}", "/ST", hh_mm, "/F"],
                                     capture_output=True, text=True, timeout=30)
                if res.returncode != 0:
                    return f"❌ فشل إنشاء المهمة المجدولة:\n{(res.stderr or res.stdout)[:800]}"
                return f"✅ تمت جدولة المهمة `{task}` يومياً الساعة {hh_mm}."
            except FileNotFoundError:
                return "❌ أداة schtasks غير متاحة على هذا النظام."
            except Exception as e:  # noqa: BLE001
                return f"❌ فشل الجدولة: {e}"

        # Linux / macOS: تثبيت حقيقي في crontab مع نسخة احتياطية
        try:
            cur = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=10)
            existing = cur.stdout if cur.returncode == 0 else ""
        except FileNotFoundError:
            return "❌ أداة crontab غير متاحة على هذا النظام."
        except Exception as e:  # noqa: BLE001
            return f"❌ فشل قراءة crontab: {e}"
        if command in existing and "THE WAY OUT" in existing:
            return "ℹ️ نفس الأمر مجدول مسبقاً — لم تتم الإضافة مجدداً."
        new_tab = (existing.rstrip() + "\n" if existing.strip() else "") + f"{fields} {command}  # THE WAY OUT\n"
        try:
            Path("crontab.backup.txt").write_text(existing, encoding="utf-8")
            res = subprocess.run(["crontab", "-"], input=new_tab,
                                 capture_output=True, text=True, timeout=10)
            if res.returncode != 0:
                return f"❌ فشل تثبيت crontab:\n{(res.stderr or res.stdout)[:500]}"
            extra = ""
            if platform.system() == "Darwin":
                extra = "\n💡 على macOS قد تحتاج منح cron صلاحية Full Disk Access من إعدادات النظام."
            return (f"✅ تمت جدولة الأمر في crontab: `{fields} {command}`\n"
                    f"📦 نسخة احتياطية من crontab القديم في `crontab.backup.txt`." + extra)
        except Exception as e:  # noqa: BLE001
            return f"❌ فشل تثبيت crontab: {e}"

    # .......................... 🤖 Advanced AI ............................
    @staticmethod
    def use_frontier_model(query: str, model: str = "") -> str:
        """سؤال موديل قوي: frontier مُعد → إجابة حقيقية، وإلا محلي + شرح الإعداد المجاني."""
        query = (query or "").strip()
        if not query:
            return "❌ حدد السؤال."
        if not frontier_configured():
            local = Tools._ask_brain(query)
            return ("ℹ️ لا يوجد مفتاح Frontier مضبوط — أجبت بالموديل المحلي "
                    f"`{get_brain().model}`:\n\n{local}\n\n{FRONTIER_SETUP_HELP}")
        mdl = (model or "").strip() or FRONTIER_MODEL
        ok, ans = frontier_chat([{"role": "user", "content": query}], model=mdl)
        if not ok:
            return f"❌ فشل طلب الـ Frontier ({mdl}): {ans}"
        return f"🌐 إجابة `{mdl}`:\n\n{ans}"

    @staticmethod
    def _run_side(query: str, name: str, installed: list) -> tuple[str, str | None, float, str]:
        """يشغّل طرفاً واحداً من المقارنة. يرجع (label, answer|None, seconds, err).

        التوجيه: `local:MODEL` للمحلي / `frontier:MODEL` للسحابي /
        تلقائي: المثبت محلياً → محلي، اسم فيه `/` → سحابي.
        """
        name = (name or "").strip()
        force = None
        if name.startswith("local:"):
            force, name = "local", name[6:].strip()
        elif name.startswith("frontier:"):
            force, name = "frontier", name[9:].strip()

        def do_frontier(mdl: str) -> tuple[str, str | None, float, str]:
            if not frontier_configured():
                return mdl or "frontier", None, 0.0, "لا يوجد مفتاح Frontier مضبوط."
            mdl = mdl or FRONTIER_MODEL
            if not mdl:
                return "frontier", None, 0.0, "FRONTIER_MODEL غير مضبوط في .env."
            t0 = time.time()
            ok, ans = frontier_chat([{"role": "user", "content": query}], model=mdl)
            dt = time.time() - t0
            if not ok:
                return mdl, None, dt, ans
            return f"frontier:{mdl}", ans, dt, ""

        def do_local(mdl: str) -> tuple[str, str | None, float, str]:
            mdl = mdl or OLLAMA_MODEL
            if installed and not any(mdl in m for m in installed):
                return mdl, None, 0.0, f"غير مثبت في Ollama (المثبت: {', '.join(installed)})."
            t0 = time.time()
            ans = AgentBrain(model=mdl).chat_simple(query)
            dt = time.time() - t0
            if ans is None:
                return mdl, None, dt, "تعذّر الاتصال بـ Ollama."
            return f"local:{mdl}", ans, dt, ""

        if force == "frontier":
            return do_frontier(name)
        if force == "local":
            return do_local(name)
        if name and any(name in m for m in installed):
            return do_local(name)
        if "/" in name:
            return do_frontier(name)
        return name, None, 0.0, (f"`{name}` غير مثبت محلياً — ثبّته (ollama pull {name}) "
                                 "أو استخدم frontier:MODEL لمقارنة سحابية.")

    @staticmethod
    def battle_models(query: str, model_a: str = "", model_b: str = "") -> str:
        """مقارنة موديلين (محلي/سحابي) على سؤال + تحكيم تلقائي."""
        query = (query or "").strip()
        if not query:
            return "❌ حدد السؤال."
        installed = get_brain().list_models()
        model_a = (model_a or "").strip() or OLLAMA_MODEL
        if not (model_b or "").strip():
            if frontier_configured():
                model_b = "frontier:"  # الموديل السحابي الافتراضي المضبوط
            else:
                plain_a = model_a.replace("local:", "")
                others = [m for m in installed if plain_a not in m]
                if not others:
                    return ("ℹ️ لا يوجد طرف ثانٍ للمقارنة — ثبّت موديلاً ثانياً "
                            "(مثال: ollama pull qwen2.5-coder:7b) أو اضبط مفتاح Frontier مجانياً.\n\n"
                            + FRONTIER_SETUP_HELP)
                model_b = others[0]
        out = [f"⚔️ مقارنة على: {query[:120]}"]
        results = []
        for side in (model_a, model_b):
            label, ans, dt, err = Tools._run_side(query, side, installed)
            if ans is None:
                out.append(f"\n--- {label}: ❌ {err}")
            else:
                results.append((label, ans))
                out.append(f"\n--- {label} ({dt:.1f}s):\n{ans[:1200]}")
        if len(results) == 2:
            (la, aa), (lb, ab) = results
            judge_prompt = (f"سؤال: {query[:300]}\n\nإجابة A ({la}):\n{aa[:1500]}\n\n"
                            f"إجابة B ({lb}):\n{ab[:1500]}\n\n"
                            "قارن باختصار: الدقة، الاكتمال، الوضوح — ثم أعلن الفائز "
                            "(A أو B أو تعادل) في سطر أخير واضح. رد بالعربي.")
            verdict, by = None, ""
            if frontier_configured():
                ok, v = frontier_chat([{"role": "user", "content": judge_prompt}], timeout=120)
                if ok:
                    verdict, by = v, FRONTIER_MODEL
            if verdict is None:
                v = get_brain().chat_simple(judge_prompt)
                if v:
                    verdict, by = v, get_brain().model
            if verdict:
                out.append(f"\n⚖️ التحكيم (بواسطة {by}):\n{verdict[:1200]}")
        return "\n".join(out)

    @staticmethod
    def run_agent_team(task: str, roles: str = "planner,executor,reviewer") -> str:
        """فريق وكلاء متسلسل: مخطط → منفّذ (بالأدوات) → مراجع."""
        task = (task or "").strip()
        if not task:
            return "❌ حدد المهمة."
        wanted = [r.strip().lower() for r in (roles or "").split(",") if r.strip()] or ["planner", "executor", "reviewer"]
        brain = get_brain()
        report = [f"🤖 فريق الوكلاء بدأ المهمة: {task[:150]}"]
        plan = ""
        if "planner" in wanted:
            plan = brain.chat_simple(
                f"مهمة: {task}\nقسّمها لخطوات مرقمة قصيرة قابلة للتنفيذ بالأدوات المتاحة "
                f"(ملفات/ترمينال/مشاريع/ويب). خطوات فقط بدون شرح طويل.",
                system="أنت مخطط مهام خبير. خطوات مرقمة مختصرة فقط.") or ""
            if not plan:
                return "❌ تعذّر الاتصال بالموديل — الفريق يحتاج Ollama شغالاً."
            report.append(f"\n📋 الخطة (planner):\n{plan[:1500]}")
        if "executor" in wanted:
            report.append("\n⚙️ التنفيذ (executor):")
            summary = run_agent(f"{task}\n\nالخطة المقترحة:\n{plan}" if plan else task,
                                brain, max_steps=AGENT_MAX_STEPS)
            report.append(summary)
        if "reviewer" in wanted:
            verdict = brain.chat_simple(
                f"مهمة: {task}\nالخطة:\n{plan[:1000]}\nراجع: هل الخطة كافية؟ ما النواقص والمخاطر؟ "
                f"رد مختصر بالعربي.",
                system="أنت مراجع جودة صارم. رد بالعربي المصري المختصر.") or ""
            report.append(f"\n🔍 المراجعة (reviewer):\n{verdict[:1500]}")
        report.append("\n🎯 انتهى عمل الفريق.")
        return "\n".join(report)

    # ............. أسماء بديلة للتوافق مع v1.x (aliases) ..................
    @staticmethod
    def list_files(path: str = ".") -> str:
        return Tools.list_directory(path)

    @staticmethod
    def read_website(url: str) -> str:
        return Tools.browse_web(url)

    @staticmethod
    def check_port(port: int, host: str = "localhost") -> str:
        return Tools.check_health(port, host)

    @staticmethod
    def launch_the_way_out(entry_file: str = "app.py", port: int = 5000) -> str:
        return Tools.launch_project(entry_file, port)

    @staticmethod
    def stop_server() -> str:
        return Tools.stop_project("wayout")


# أسماء بديلة يقبلها الموجّه عند استدعاء الموديل لأداة قديمة
TOOL_ALIASES = {
    # أسماء قديمة (v1.x) — للتوافق
    "list_files": "list_directory", "read_website": "browse_web",
    "check_port": "check_health", "launch_the_way_out": "launch_project",
    "stop_server": "stop_project",
    # أخطاء الموديلات الصغيرة الشائعة → الأداة الصحيحة
    "read_web": "browse_web", "read_url": "browse_web", "fetch_url": "browse_web",
    "open_url": "browse_web", "get_url": "browse_web", "fetch": "browse_web",
    "run_command": "execute_terminal", "shell": "execute_terminal",
    "terminal": "execute_terminal", "cmd": "execute_terminal", "bash": "execute_terminal",
    "run_file": "run_python", "python": "run_python", "exec_python": "run_python",
    "write": "write_file", "create_file": "write_file", "save_file": "write_file",
    "read": "read_file", "open_file": "read_file", "cat": "read_file",
    "list": "list_directory", "ls": "list_directory", "dir": "list_directory",
    "delete": "delete_file", "remove_file": "delete_file", "rm": "delete_file",
    "search": "search_files", "find": "search_files", "grep": "search_files",
    "find_in_files": "search_files",
    "health": "check_health", "status": "check_health", "ping": "check_health",
    "logs": "read_logs", "log": "read_logs", "get_logs": "read_logs",
    "launch": "launch_project", "start": "launch_project", "serve": "launch_project",
    "stop": "stop_project", "kill": "stop_project",
    "monitor": "monitor_project", "watch": "monitor_project",
    "project": "create_project", "new_project": "create_project", "scaffold": "create_project",
    "search_web": "web_search", "google": "web_search", "websearch": "web_search",
    "search_internet": "web_search",
    "download": "download_file", "fetch_file": "download_file", "wget": "download_file",
    "api": "call_api", "http": "call_api", "request": "call_api",
    "scrape": "scrape_data", "crawl": "scrape_data",
    "analyze": "analyze_code", "analyse": "analyze_code",
    "review": "review_code", "explain": "explain_code",
    "bugs": "find_bugs", "debug": "find_bugs",
    "test": "generate_tests", "tests": "generate_tests", "unittest": "generate_tests",
    "refactor": "refactor_code",
    "readme": "generate_readme", "read_me": "generate_readme",
    "docs": "generate_documentation", "document": "generate_documentation",
    "content": "generate_content",
    "automate": "create_automation", "automation": "create_automation",
    "schedule": "schedule_task", "cron": "schedule_task",
    "team": "run_agent_team", "agents": "run_agent_team",
    "battle": "battle_models", "compare_models": "battle_models",
    "frontier": "use_frontier_model", "gpt": "use_frontier_model", "Muse": "use_frontier_model",
    "system": "check_system", "sysinfo": "check_system", "sys_info": "check_system",
    "install": "install_package", "pip": "install_package", "pip_install": "install_package",
    "remember_fact": "remember", "memorize": "remember", "save_memory": "remember",
    "memory": "list_memories", "memories": "list_memories",
}

TOOLSET_CORE = ["execute_terminal", "write_file", "read_file", "list_directory",
                "launch_project", "browse_web", "check_health"]

# ===========================================================================
# تعريف الأدوات للموديل (Ollama Tool Calling schema) — أوصاف مختصرة عمداً
# ===========================================================================
_TOOL = lambda name, desc, props, req=(): {  # noqa: E731
    "name": name, "description": desc,
    "parameters": {"type": "object", "properties": props,
                   **({"required": list(req)} if req else {})}}

TOOLS_SCHEMA = {
    # 📁
    "write_file": _TOOL("write_file", "إنشاء أو تعديل ملف.",
                        {"path": {"type": "string"}, "content": {"type": "string"}}, ("path", "content")),
    "read_file": _TOOL("read_file", "قراءة ملف.", {"path": {"type": "string"}}, ("path",)),
    "edit_file": _TOOL("edit_file", "تعديل جزء محدد داخل ملف.",
                       {"path": {"type": "string"}, "find": {"type": "string"},
                        "replace": {"type": "string"}}, ("path", "find", "replace")),
    "list_directory": _TOOL("list_directory", "عرض محتويات مجلد.",
                            {"path": {"type": "string"}}),
    "delete_file": _TOOL("delete_file", "حذف ملف (للمهم أكّد مع المستخدم أولاً).",
                         {"path": {"type": "string"}}, ("path",)),
    "search_files": _TOOL("search_files", "بحث بنمط داخل ملفات مجلد.",
                          {"pattern": {"type": "string"}, "directory": {"type": "string"}}, ("pattern",)),
    # 💻
    "execute_terminal": _TOOL("execute_terminal", "تنفيذ أمر ترمينال (التدميري محظور).",
                              {"command": {"type": "string"}}, ("command",)),
    "run_python": _TOOL("run_python", "تشغيل كود بايثون أو ملف .py.",
                        {"code_or_file": {"type": "string"}}, ("code_or_file",)),
    "install_package": _TOOL("install_package", "تثبيت مكتبة pip.",
                             {"package_name": {"type": "string"}}, ("package_name",)),
    "check_system": _TOOL("check_system", "فحص النظام (CPU/RAM/Disk).", {}),
    # 🚀
    "create_project": _TOOL("create_project", "إنشاء مشروع من قالب: basic/flask/fastapi/static.",
                            {"name": {"type": "string"}, "template": {"type": "string"}}, ("name",)),
    "launch_project": _TOOL("launch_project", "تشغيل مشروع محلياً على منفذ.",
                            {"entry_file": {"type": "string"}, "port": {"type": "integer"},
                             "name": {"type": "string"}}),
    "stop_project": _TOOL("stop_project", "إيقاف مشروع شغال.", {"name": {"type": "string"}}),
    "check_health": _TOOL("check_health", "فحص هل منفذ/سيرفر شغال.",
                          {"port": {"type": "integer"}, "host": {"type": "string"}}, ("port",)),
    "read_logs": _TOOL("read_logs", "قراءة لوجات مشروع.",
                       {"project": {"type": "string"}, "lines": {"type": "integer"}}),
    "monitor_project": _TOOL("monitor_project", "مراقبة مشروع (حالة+منفذ+لوجات).",
                             {"name": {"type": "string"}}),
    # 🌐
    "browse_web": _TOOL("browse_web", "قراءة محتوى موقع.", {"url": {"type": "string"}}, ("url",)),
    "web_search": _TOOL("web_search", "بحث إنترنت (بدون API key).",
                        {"query": {"type": "string"}, "max_results": {"type": "integer"}}, ("query",)),
    "download_file": _TOOL("download_file", "تنزيل ملف (حد 50MB).",
                           {"url": {"type": "string"}, "destination": {"type": "string"}}, ("url", "destination")),
    "call_api": _TOOL("call_api", "استدعاء API (GET/POST/PUT/DELETE).",
                      {"url": {"type": "string"}, "method": {"type": "string"},
                       "headers": {"type": "string"}, "body": {"type": "string"}}, ("url",)),
    "scrape_data": _TOOL("scrape_data", "سحب بيانات من موقع (selector اختياري).",
                         {"url": {"type": "string"}, "selector": {"type": "string"}}, ("url",)),
    # 🧠
    "remember": _TOOL("remember", "حفظ معلومة في الذاكرة الدائمة.",
                      {"fact": {"type": "string"}, "category": {"type": "string"}}, ("fact",)),
    "recall": _TOOL("recall", "استرجاع من الذاكرة.", {"query": {"type": "string"}}, ("query",)),
    "list_memories": _TOOL("list_memories", "عرض الذاكرة.", {"category": {"type": "string"}}),
    "forget": _TOOL("forget", "نسيان معلومة برقمها.", {"fact_id": {"type": "integer"}}, ("fact_id",)),
    # 🔧
    "analyze_code": _TOOL("analyze_code", "تحليل كود.", {"file": {"type": "string"}}, ("file",)),
    "review_code": _TOOL("review_code", "مراجعة كود.", {"file": {"type": "string"}}, ("file",)),
    "explain_code": _TOOL("explain_code", "شرح كود بالعربي.", {"file": {"type": "string"}}, ("file",)),
    "find_bugs": _TOOL("find_bugs", "البحث عن أخطاء في كود.", {"file": {"type": "string"}}, ("file",)),
    "generate_tests": _TOOL("generate_tests", "توليد اختبارات pytest لملف.",
                            {"file": {"type": "string"}}, ("file",)),
    "refactor_code": _TOOL("refactor_code", "إعادة هيكلة ملف (مع .bak).",
                           {"file": {"type": "string"}, "goal": {"type": "string"}}, ("file",)),
    # 🎨
    "generate_readme": _TOOL("generate_readme", "كتابة README لمشروع.",
                             {"project": {"type": "string"}}),
    "generate_documentation": _TOOL("generate_documentation", "توليد توثيق لملف.",
                                    {"file": {"type": "string"}}, ("file",)),
    "generate_content": _TOOL("generate_content", "إنشاء محتوى (article/post/script).",
                              {"topic": {"type": "string"}, "type": {"type": "string"}}, ("topic",)),
    # 📊
    "create_automation": _TOOL("create_automation", "إنشاء أتمتة (trigger+action).",
                               {"trigger": {"type": "string"}, "action": {"type": "string"}}, ("action",)),
    "schedule_task": _TOOL("schedule_task", "جدولة حقيقية (schtasks/crontab) — يقبل HH:MM أو cron.",
                           {"cron": {"type": "string"}, "command": {"type": "string"}}, ("command",)),
    # 🤖
    "use_frontier_model": _TOOL("use_frontier_model", "سؤال موديل قوي (يحتاج FRONTIER_API_KEY مجاني وإلا يُجاب محلياً).",
                                {"query": {"type": "string"}, "model": {"type": "string"}}, ("query",)),
    "battle_models": _TOOL("battle_models", "مقارنة موديلين (local:/frontier:) مع تحكيم تلقائي.",
                           {"query": {"type": "string"}, "model_a": {"type": "string"},
                            "model_b": {"type": "string"}}, ("query",)),
    "run_agent_team": _TOOL("run_agent_team", "فريق وكلاء: مخطط→منفّذ→مراجع.",
                            {"task": {"type": "string"}, "roles": {"type": "string"}}, ("task",)),
}


def build_tools_schema(toolset: str = "full") -> list:
    names = TOOLSET_CORE if toolset == "core" else list(TOOLS_SCHEMA.keys())
    return [{"type": "function", "function": TOOLS_SCHEMA[n]} for n in names]


# ===========================================================================
# 🧠 عقل الإيجنت (Ollama)
# ===========================================================================
class AgentBrain:
    def __init__(self, model: str = OLLAMA_MODEL, base_url: str = OLLAMA_BASE_URL):
        self.model = model
        self.base_url = base_url.rstrip("/")

    def list_models(self) -> list:
        try:
            with urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return [m.get("name", "") for m in data.get("models", [])]
        except Exception:
            return []

    def check_connection(self) -> tuple[bool, str]:
        models = self.list_models()
        if models is None:  # pragma: no cover
            return False, "خطأ غير متوقع."
        if not models:
            # قد يكون متصلاً لكن بلا موديلات، أو غير متصل أصلاً — نميّز بمحاولة سريعة
            try:
                urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=5).read()
                return False, "متصل لكن لا توجد موديلات — نفّذ: ollama run qwen2.5-coder:1.5b"
            except Exception as e:  # noqa: BLE001
                return False, f"تعذّر الاتصال بـ Ollama على {self.base_url} — {e}"
        if any(self.model in m for m in models):
            return True, f"متصل — الموديل `{self.model}` جاهز. ✅"
        return False, f"متصل لكن الموديل `{self.model}` غير موجود. المتاح: {models}"

    def _post_chat(self, payload: dict, timeout: int) -> dict | None:
        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            return None

    def query(self, messages: list, tools: list | None = None) -> dict:
        payload = {"model": self.model, "messages": messages, "stream": False,
                   "options": {"temperature": 0.1, "num_ctx": OLLAMA_NUM_CTX, "num_predict": 1024}}
        if tools:
            payload["tools"] = tools
        data = self._post_chat(payload, timeout=180)
        if data is None:
            return {"role": "assistant",
                    "content": (f"❌ خطأ في الاتصال بالموديل — تأكد أن Ollama شغال "
                                f"والموديل `{self.model}` موجود (جرّب: ollama run {self.model}).")}
        return data.get("message", {"role": "assistant", "content": ""})

    def chat_simple(self, prompt: str, system: str | None = None,
                    timeout: int = 180) -> str | None:
        """محادثة بدون أدوات (تُستخدم داخل مهارات التحليل والمحتوى والفريق)."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {"model": self.model, "messages": messages, "stream": False,
                   "options": {"temperature": 0.3, "num_ctx": OLLAMA_NUM_CTX}}
        data = self._post_chat(payload, timeout=timeout)
        if data is None:
            return None
        return (data.get("message", {}).get("content", "") or "").strip() or None


_BRAIN_SINGLETON: AgentBrain | None = None


def get_brain() -> AgentBrain:
    global _BRAIN_SINGLETON
    if _BRAIN_SINGLETON is None:
        _BRAIN_SINGLETON = AgentBrain()
    return _BRAIN_SINGLETON


# ===========================================================================
# 🎬 حلقة التنفيذ (ReAct + Self-Healing)
# ===========================================================================
def _parse_tool_args(raw_args) -> dict:
    if isinstance(raw_args, dict):
        return raw_args
    if isinstance(raw_args, str):
        try:
            parsed = json.loads(raw_args)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _normalize_tool_args(args: dict) -> dict:
    """يفك أغلفة {type,value} التي تكتبها الموديلات الصغيرة ويحوّل القواميس لنصوص."""
    norm = {}
    for k, v in (args or {}).items():
        if isinstance(v, dict) and "value" in v and len(v) <= 3:
            v = v["value"]
        if isinstance(v, (dict, list)):
            v = json.dumps(v, ensure_ascii=False)
        norm[k] = v
    return norm


def extract_text_tool_calls(content: str) -> list:
    """مُنقذ الموديلات الصغيرة: يستخرج استدعاءات أدوات من JSON مكتوب كنص.

    يقبل: بلوكات ```json و JSON خام، وبأشكال {name,arguments} أو
    {function:{name,arguments}} أو {tool,parameters}. يرجع قائمة
    [{name, arguments}] للأدوات المعروفة فقط (حد أقصى 3).
    """
    if not content or "{" not in content or "}" not in content:
        return []
    candidates: list[str] = []
    for m in re.finditer(r"```(?:json)?\s*\n(.*?)```", content, flags=re.S | re.I):
        candidates.append(m.group(1))
    if not candidates:
        m = re.search(r"\{.*\}", content, flags=re.S)
        if m:
            candidates.append(m.group(0))
    calls = []
    for c in candidates:
        try:
            obj = json.loads(c.strip())
        except json.JSONDecodeError:
            continue
        items = obj if isinstance(obj, list) else [obj]
        for it in items:
            if not isinstance(it, dict):
                continue
            name, args = None, {}
            if "name" in it and isinstance(it.get("name"), str):
                name, args = it["name"], _parse_tool_args(it.get("arguments", {}))
            elif isinstance(it.get("function"), dict):
                fn = it["function"]
                name, args = fn.get("name"), _parse_tool_args(fn.get("arguments", {}))
            elif "tool" in it and isinstance(it.get("tool"), str):
                name = it["tool"]
                args = _parse_tool_args(it.get("parameters", it.get("arguments", {})))
            if not name or not isinstance(name, str):
                continue
            resolved, fix_note = resolve_tool_name(name)
            if not resolved:
                continue
            name = resolved
            calls.append({"name": name, "arguments": _normalize_tool_args(args), "note": fix_note})
            if len(calls) >= 3:
                return calls
    return calls


def _auto_summary(history: list, tools_used: int, dt: float, reason: str) -> str:
    """ملخص محلي تلقائي عندما يعجز الموديل الصغير عن إنهاء المهمة بنفسه."""
    title = ("🔁 أوقفت التكرار — وهذا ملخص ما تم:" if reason == "loop"
             else "🎯 ملخص ما تم قبل انتهاء الخطوات:")
    lines = [title]
    for i, (name, args, ok, snippet) in enumerate(history, 1):
        if i > 10:
            lines.append(f"… +{len(history) - 10} خطوات أخرى")
            break
        icon = "✅" if ok else "❌"
        arg_hint = ""
        if isinstance(args, dict):
            for k in ("path", "file", "project", "url", "query", "command", "port", "name"):
                if args.get(k) not in (None, ""):
                    arg_hint = f"({args[k]})"
                    break
        first_line = snippet.splitlines()[0][:120] if snippet else ""
        lines.append(f"{icon} {i}. {name}{arg_hint} — {first_line}")
    if not history:
        lines.append("(لم تُنفَّذ أي أداة)")
    lines.append(f"📊 (الأدوات المستخدمة: {tools_used} | الوقت: {dt:.1f}s)")
    return "\n".join(lines)


_INTENT_LAUNCH = ["شغّل مشروع", "شغل مشروع", "شغّلي المشروع", "شغل السيرفر",
                 "شغّل السيرفر", "launch project", "start project", "run project",
                 "start server", "launch server"]
_INTENT_PORT = ["افحص المنفذ", "افحص منفذ", "افحص البورت", "check port", "test port"]
_INTENT_FILES = ["اعرض الملفات", "محتويات المجلد", "قائمة الملفات", "list files",
                 "show files", "اعرض محتويات"]


def _match_intent(query: str):
    """يطابق نية آمنة واضحة. يرجع (اسم_الأداة, kwargs) أو None. (دالة خالصة — بدون تنفيذ)"""
    q = (query or "").strip().lower()
    if not q:
        return None
    if any(k in q for k in _INTENT_LAUNCH):
        m = re.search(r"(\d{2,5})", q)
        return ("launch_project", {"port": int(m.group(1)) if m else 5000})
    if any(k in q for k in _INTENT_PORT):
        m = re.search(r"(\d{2,5})", q)
        if m:
            return ("check_health", {"port": int(m.group(1))})
        return None
    if any(k in q for k in _INTENT_FILES):
        return ("list_directory", {})
    return None


_GOAL_READ = ["اقرأ موقع", "افتح موقع", "لخص", "لخّص", "محتوى الموقع", "تصفح",
              "read website", "browse", "summarize", "summarise", "open url", "http"]
_GOAL_SEARCH = ["ابحث", "بحث", "search", "دور على", "دوّر على"]
_GOAL_FILE = ["اقرأ ملف", "افتح ملف", "read file", "open file", "اعرض ملف"]


def _goal_tools(query: str) -> set:
    """الأدوات التي يعتبر نجاحها إنجازاً لهدف المستخدم (لا استدعاء — دالة خالصة)."""
    q = (query or "").strip().lower()
    goals = set()
    if any(k in q for k in _GOAL_READ):
        goals.add("browse_web")
    if any(k in q for k in _GOAL_SEARCH):
        goals |= {"web_search", "browse_web"}
    if any(k in q for k in _GOAL_FILE):
        goals.add("read_file")
    intent = _match_intent(query)
    if intent:
        goals.add(intent[0])
    return goals


def _goal_satisfied(query: str, fn_name: str) -> bool:
    """هل نجاح هذه الأداة يحقق هدف المستخدم؟"""
    return bool(fn_name) and fn_name in _goal_tools(query)


def _goal_summary(query: str, fn_name: str, result: str,
                  tools_used: int, dt: float) -> str:
    """تسليم النتيجة المُحقِّقة للهدف عندما يعجز الموديل عن كتابة الملخص."""
    body = (result or "").strip()
    if len(body) > 1800:
        body = body[:1800] + " …"
    return (f"✅ المهمة اتنفذت (عبر `{fn_name}`) — الموديل تاه بعدها، "
            f"فبسلّمك الناتج مباشرة:\n\n{body}\n\n"
            f"📊 (الأدوات المستخدمة: {tools_used} | الوقت: {dt:.1f}s)")


def _route_intent(query: str):
    """الملاذ الأخير: ينفذ نية آمنة واضحة مباشرة. يرجع (الاسم, النتيجة) أو (None, '')."""
    m = _match_intent(query)
    if not m:
        return None, ""
    name, kwargs = m
    try:
        return name, str(getattr(Tools, name)(**kwargs))
    except Exception as e:  # noqa: BLE001
        return name, f"❌ فشل التوجيه المباشر: {e}"


_ACTION_MARKERS_AR = ["اعمل", "اكتب", "أنشئ", "انشئ", "شغّل", "شغل", "افحص", "افتح",
                      "اقرأ", "اقرا", "ابحث", "دور على", "دوّر", "ثبّت", "ثبت",
                      "احفظ", "سجّل", "احذف", "امسح", "عدّل", "عدل", "غيّر",
                      "صلّح", "اصلح", "أصلح", "نفّذ", "نفذ", "نزّل", "نزل",
                      "حمّل", "حمل", "راجع", "حلّل", "اشرح", "قارن", "لخّص",
                      "لخص", "جدول", "أتمت", "اتمت", "راقب", "أوقف", "وقف",
                      "ابني", "استخرج", "اسحب", "ضيف", "أضف", "ترجم", "اختصر"]
_ACTION_MARKERS_EN = ["make", "create", "write", "run", "launch", "start", "check",
                      "read", "search", "install", "save", "delete", "remove", "edit",
                      "update", "fix", "execute", "download", "review", "analy",
                      "explain", "compare", "summar", "schedule", "automate",
                      "monitor", "stop", "build", "generate", "fetch", "open"]
_QUESTION_MARKERS = ["؟", "?", "ازاي", "ازاى", "ليه", "لماذا", "ايه", "إيه",
                     "ماهو", "ما هو", "مين", "امتى", "متى", "فين",
                     "أين", "يعني ايه", "what", "how", "why", "when",
                     "where", "who", "which"]


def _looks_like_action(query: str) -> bool:
    """هل الطلب مهمة تنفيذية (تحتاج أدوات) أم سؤال/دردشة؟"""
    q = (query or "").strip().lower()
    if not q:
        return False
    padded = f" {q} "
    is_question = (" هل " in padded or any(m in q for m in _QUESTION_MARKERS))
    if any(m in q for m in _ACTION_MARKERS_AR):
        return not is_question
    for w in _ACTION_MARKERS_EN:
        if re.search(r"\b" + re.escape(w) + r"\w*\b", q):
            return not is_question
    return False


def resolve_tool_name(name: str) -> tuple[str | None, str]:
    """يحل اسم أداة (صحيح/بديل/مقارب إملائياً). يرجع (الحقيقي, ملاحظة) أو (None, '')."""
    if not name or not isinstance(name, str):
        return None, ""
    name = name.strip()
    if name in TOOLS_SCHEMA:
        return name, ""
    if name in TOOL_ALIASES:
        return TOOL_ALIASES[name], f"فسّرت `{name}` كـ `{TOOL_ALIASES[name]}`"
    close = difflib.get_close_matches(name, list(TOOLS_SCHEMA.keys()), n=1, cutoff=0.8)
    if close:
        return close[0], f"صححت `{name}` إلى `{close[0]}`"
    return None, ""


def _looks_failed(result: str) -> bool:
    return result.startswith(("❌", "⛔", "⚠️"))


def run_agent(user_query: str, brain: AgentBrain,
              max_steps: int = AGENT_MAX_STEPS,
              toolset: str = AGENT_TOOLSET) -> str:
    """ينفذ طلباً كاملاً بحلقة ReAct. يرجع ملخصاً نصياً (ويطبع أثناء العمل)."""
    tools_schema = build_tools_schema(toolset)
    messages: list = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_query},
    ]
    print(f"\n{Fore.CYAN}🧠 الإيجنت بيفكر ويخطط...{Style.RESET_ALL}")
    t0 = time.time()
    tools_used = 0
    fail_counts: dict[str, int] = {}
    last_text = ""
    success_key = ""
    success_streak = 0
    history: list = []
    nudges_used = 0

    goal_done = None  # (fn_name, result) لأول نجاح يحقق هدف المستخدم
    for step in range(1, max_steps + 1):
        msg = brain.query(messages, tools_schema)
        content = msg.get("content", "") or ""
        tool_calls = msg.get("tool_calls", []) or []

        if content.strip():
            last_text = content.strip()
            print(f"{Fore.YELLOW}💭 الإيجنت: {content}{Style.RESET_ALL}")

        # مُنقذ الموديلات الصغيرة: لو كتبت JSON كنص بدل استدعاء حقيقي — التقطه ونفّذه
        if not tool_calls and content.strip():
            rescued = extract_text_tool_calls(content)
            if rescued:
                print(f"{Fore.CYAN}🔧 (الموديل كتب JSON كنص — التقطت {len(rescued)} استدعاء وأنفّذه){Style.RESET_ALL}")
                for _c in rescued:
                    if _c.get("note"):
                        print(f"{Fore.CYAN}   🔤 {_c['note']}{Style.RESET_ALL}")
                tool_calls = [{"function": {"name": c["name"], "arguments": c["arguments"]}} for c in rescued]

        if not tool_calls:
            if content.strip().startswith("❌ خطأ في الاتصال"):
                print(f"\n{Fore.RED}{content}{Style.RESET_ALL}\n")
                return content
            # No-action guard: ارفض الادعاء بدون تنفيذ للمهام التنفيذية (محاولتان ثم توجيه حتمي)
            if tools_used == 0 and _looks_like_action(user_query):
                if nudges_used < 2:
                    nudges_used += 1
                    last_text = ""
                    print(f"{Fore.YELLOW}⚠️ (رد بدون تنفيذ — أطالبه بالتنفيذ الحقيقي... محاولة {nudges_used}/2){Style.RESET_ALL}")
                    if nudges_used == 1:
                        nudge_text = (
                            "⛔ لم تستخدم أي أداة! المطلوب مهمة تنفيذية — ممنوع الادعاء بأن شيئاً تم بدون تنفيذه فعلاً. "
                            "نفّذ الآن باستدعاء الأداة المناسبة "
                            "(تشغيل مشروع → launch_project | كتابة ملف → write_file | قراءة → read_file | "
                            "فحص منفذ → check_health | بحث ويب → web_search | تنفيذ أمر → execute_terminal). "
                            "ممنوع كتابة التقرير النهائي قبل التنفيذ والتحقق. " f"المطلوب الأصلي: {user_query[:200]}")
                    else:
                        nudge_text = ("FINAL WARNING (read carefully, in English): You MUST call a tool NOW. "
                            "Do NOT write Arabic text. Do NOT repeat your previous answer. "
                            "Launching/running → call launch_project. Writing → write_file. "
                            "CALL THE TOOL IN THIS RESPONSE, no excuses. " f"ORIGINAL TASK: {user_query[:200]}")
                    messages.append(msg)
                    messages.append({"role": "user", "content": nudge_text})
                    continue
                # المحاولات خلصت — الملاذ الأخير: التوجيه الحتمي المباشر
                rname, rres = _route_intent(user_query)
                if rname:
                    tools_used += 1
                    history.append((rname, {}, not _looks_failed(rres), str(rres)[:150]))
                    print(f"{Fore.CYAN}🤖 (الموديل رفض التنفيذ مرتين — نفّذت الأمر مباشرة: {rname}){Style.RESET_ALL}")
                    print(f"{Fore.MAGENTA}   ↳ الناتج: {str(rres)[:250]}{Style.RESET_ALL}")
                    final = f"🤖 نفّذت طلبك مباشرة (الموديل الصغير رفض التعاون):\n{rres}"
                    print(f"\n{Fore.GREEN}🎯 النتيجة:\n{final}{Style.RESET_ALL}")
                    dt = time.time() - t0
                    print(f"{Fore.CYAN}📊 (الأدوات المستخدمة: {tools_used} | الوقت: {dt:.1f}s){Style.RESET_ALL}\n")
                    return f"{final}\n📊 (الأدوات المستخدمة: {tools_used} | الوقت: {dt:.1f}s)"
                print(f"{Fore.RED}❌ الموديل رفض التنفيذ بعد محاولتين، والطلب غير قابل للتوجيه المباشر.{Style.RESET_ALL}")
                print(f"{Fore.YELLOW}💡 جرّب: إعادة صياغة الأمر، أو الوضع الخفيف (--toolset core)، أو مفتاح Frontier مجاني.{Style.RESET_ALL}")
            print(f"\n{Fore.GREEN}🎯 النتيجة:\n{content or '(لا يوجد رد نصي)'}{Style.RESET_ALL}")
            break

        messages.append(msg)
        for tool in tool_calls:
            fn = tool.get("function", {})
            raw_name = fn.get("name", "")
            resolved, fix_note = resolve_tool_name(raw_name)
            fn_name = resolved or raw_name
            if fix_note:
                print(f"{Fore.CYAN}   🔤 {fix_note}{Style.RESET_ALL}")
            args = _parse_tool_args(fn.get("arguments", {}))
            print(f"{Fore.BLUE}⚙️ [تنفيذ {step}/{max_steps}]: {fn_name}({args}){Style.RESET_ALL}")

            tool_fn = getattr(Tools, fn_name, None)
            if tool_fn is None:
                result = f"❌ الأداة `{fn_name}` غير موجودة."
            else:
                try:
                    result = str(tool_fn(**args))
                except TypeError as e:
                    result = f"❌ خطأ في باراميترات `{fn_name}`: {e}"
                except Exception as e:  # noqa: BLE001
                    result = f"❌ فشل تنفيذ `{fn_name}`: {e}"

            tools_used += 1
            print(f"{Fore.MAGENTA}   ↳ الناتج: {result[:250]}{Style.RESET_ALL}")

            # Self-healing guard: امنع تكرار نفس الاستدعاء الفاشل أكثر من 3 مرات
            # Loop guard: أوقف تكرار نفس الاستدعاء *الناجح* 3 مرات ولخّص تلقائياً
            key = fn_name + json.dumps(args, sort_keys=True, ensure_ascii=False)
            history.append((fn_name, args, not _looks_failed(result), str(result)[:150]))
            if _looks_failed(result):
                success_streak = 0
                success_key = ""
                fail_counts[key] = fail_counts.get(key, 0) + 1
                if goal_done is not None and fail_counts[key] >= 2:
                    dt = time.time() - t0
                    print(f"\n{Fore.YELLOW}🎯 الهدف تحقق قبل كده — بوقف اللف وأسلّم "
                          f"ناتج `{goal_done[0]}`.{Style.RESET_ALL}")
                    final = _goal_summary(user_query, goal_done[0], goal_done[1],
                                          tools_used, dt)
                    print(f"{Fore.GREEN}{final}{Style.RESET_ALL}\n")
                    return final
                if fail_counts[key] >= 3:
                    # إنقاذ أخير: نفّذ النية الآمنة الواضحة مباشرة قبل الاستسلام
                    rname, rres = _route_intent(user_query)
                    if rname:
                        tools_used += 1
                        history.append((rname, {}, not _looks_failed(rres), str(rres)[:150]))
                        print(f"\n{Fore.CYAN}🤖 (الموديل فشل 3 مرات — نفّذت النية مباشرة: {rname}){Style.RESET_ALL}")
                        print(f"{Fore.MAGENTA}   ↳ الناتج: {str(rres)[:250]}{Style.RESET_ALL}")
                        final = f"🤖 الموديل تعثر 3 مرات، فنفّذت طلبك مباشرة:\n{rres}"
                        print(f"\n{Fore.GREEN}🎯 النتيجة:\n{final}{Style.RESET_ALL}")
                        dt = time.time() - t0
                        print(f"{Fore.CYAN}📊 (الأدوات المستخدمة: {tools_used} | الوقت: {dt:.1f}s){Style.RESET_ALL}\n")
                        return f"{final}\n📊 (الأدوات المستخدمة: {tools_used} | الوقت: {dt:.1f}s)"
                    note = ("\n(⛔ تنبيه النظام: كررت نفس الاستدعاء الفاشل 3 مرات — "
                            "توقف فوراً، اشرح المشكلة للمستخدم بالعربي، واقترح حلاً بديلاً.)")
                    messages.append({"role": "tool", "name": fn_name, "content": result + note})
                    print(f"\n{Fore.RED}🛑 تكرار فاشل 3 مرات — إيقاف الحلقة.{Style.RESET_ALL}\n")
                    return f"❌ توقفت بعد 3 محاولات فاشلة لنفس الاستدعاء: {fn_name} — راجع الخطأ أعلاه."
                result += "\n(تلميح: فشل التنفيذ — جرّب حلاً بديلاً مختلفاً، ولا تكرر نفس الاستدعاء بحذافيره.)"
                intent = _match_intent(user_query)
                if intent and intent[0] != fn_name:
                    result += f"\n(تلميح قوي: المطلوب على الأرجح `{intent[0]}` — استدعِه الآن بدلاً من تكرار `{fn_name}`.)"
            else:
                fail_counts.clear()
                if goal_done is None and _goal_satisfied(user_query, fn_name):
                    goal_done = (fn_name, result)
                    result += ("\n(✅ تنبيه النظام: دي كانت المهمة المطلوبة وقد نجحت. "
                               "توقف عن استدعاء الأدوات فوراً واكتب الملخص النهائي "
                               "بالعربي كنص عادي بدون JSON.)")
                if key == success_key:
                    success_streak += 1
                else:
                    success_key, success_streak = key, 1
                if success_streak == 2:
                    result += "\n(تنبيه: كررت نفس الاستدعاء الناجح — لو المهمة اكتملت اكتب التقرير النهائي الآن (نص عربي بدون JSON) وتوقف عن الأدوات.)"
                elif success_streak >= 3:
                    messages.append({"role": "tool", "name": fn_name, "content": result})
                    print(f"\n{Fore.YELLOW}🔁 تكرار نفس الخطوة الناجحة 3 مرات — أوقف الحلقة وألخص.{Style.RESET_ALL}")
                    summary = _auto_summary(history, tools_used, time.time() - t0, reason="loop")
                    print(f"{Fore.GREEN}{summary}{Style.RESET_ALL}\n")
                    return summary

            messages.append({"role": "tool", "name": fn_name, "content": result})
    else:
        last_text = f"⚠️ وصلت لأقصى عدد خطوات ({max_steps}) — جرّب تقسيم طلبك لأجزاء أصغر."
        print(f"\n{Fore.YELLOW}{last_text}{Style.RESET_ALL}")
        summary = _auto_summary(history, tools_used, time.time() - t0, reason="steps")
        print(f"{Fore.GREEN}{summary}{Style.RESET_ALL}\n")
        return summary

    dt = time.time() - t0
    print(f"{Fore.CYAN}📊 (الأدوات المستخدمة: {tools_used} | الوقت: {dt:.1f}s){Style.RESET_ALL}\n")
    return f"{last_text}\n📊 (الأدوات المستخدمة: {tools_used} | الوقت: {dt:.1f}s)"


# ===========================================================================
# 🔍 الفحص الذاتي (بدون موديل)
# ===========================================================================
def self_check() -> int:
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

    with tempfile.TemporaryDirectory() as tmp:
        os.environ["MEMORY_FILE"] = str(Path(tmp) / "mem.json")

        # 📁 ملفات
        p = str(Path(tmp) / "hello.txt")
        r1 = Tools.write_file(p, "print('hello')\n# v1")
        report("write_file", "تم إنشاء" in r1)
        report("read_file", "hello" in Tools.read_file(p))
        r2 = Tools.edit_file(p, "v1", "v2")
        report("edit_file", "تم تعديل" in r2 and "v2" in Tools.read_file(p))
        report("edit_file لنص غير موجود", "غير موجود" in Tools.edit_file(p, "zzz", "y"))
        report("list_directory", "hello.txt" in Tools.list_directory(tmp))
        report("search_files", "hello.txt" in Tools.search_files("hello", tmp))
        report("delete_file", "تم حذف" in Tools.delete_file(p) and not Path(p).exists())

        # 💻 نظام
        report("execute_terminal (آمن)", "hello-check" in Tools.execute_terminal("echo hello-check"))
        report("حظر أمر تدميري", "محظور" in Tools.execute_terminal("rm -rf / --no-preserve-root"))
        report("run_python (كود)", "7" in Tools.run_python("print(3+4)"))
        missing = Tools.run_python(str(Path(tmp) / "nope.py"))
        report("run_python (ملف مفقود)", "غير موجود" in missing)
        report("check_system", "CPU" in Tools.check_system())

        # 🧠 ذاكرة
        report("remember", "تم الحفظ" in Tools.remember("المستخدم يفضل Flask", "prefs"))
        report("recall", "Flask" in Tools.recall("يفضل المستخدم"))
        report("list_memories", "Flask" in Tools.list_memories())
        report("forget", "تم نسيان" in Tools.forget(1))

        # 🚀 مشاريع
        old_cwd = os.getcwd()
        os.chdir(tmp)
        try:
            r3 = Tools.create_project("demo1", "basic")
            report("create_project", "تم إنشاء" in r3 and Path("demo1/app.py").exists())
            r_fz = Tools.create_project("demo2", "basic/flask/fastapi/static")
            report("create_project (قالب مشوش)", "تم إنشاء" in r_fz and "فسّرت" in r_fz)
            s = socket.socket()
            s.bind(("127.0.0.1", 0))
            free_port = s.getsockname()[1]
            s.close()
            r4 = Tools.launch_project(entry_file="srv.py", port=free_port, name="t1")
            ok_srv = f"localhost:{free_port}" in r4 or "تم تشغيل" in r4
            report("launch_project", ok_srv, r4[:100])
            report("check_health", "مفتوح" in Tools.check_health(free_port))
            report("read_logs", "Server starting" in Tools.read_logs("t1") or "آخر" in Tools.read_logs("t1"))
            report("monitor_project", "شغال" in Tools.monitor_project("t1"))
            # call_api ضد السيرفر المحلي
            r5 = Tools.call_api(f"http://127.0.0.1:{free_port}/")
            report("call_api (محلي)", "HTTP 200" in r5, r5[:80])
            report("stop_project", "تم إيقاف" in Tools.stop_project("t1"))
            Tools.write_file("quick.py", 'print("done-quick")')
            r_nano = Tools.launch_project(entry_file="quick.py", port=free_port, name="nano")
            Tools.stop_project("nano")
            report("launch_project (سكربت مش سيرفر)", "مش سيرفر" in r_nano, r_nano[:100])
            # الجدولة (وضع تجريبي آمن — لا يمس النظام)
            os.environ["SCHEDULE_DRY_RUN"] = "1"
            r_dry = Tools.schedule_task("09:30", "echo sched-test")
            report("schedule_task (تجريبي)", "30 9 * * *" in r_dry and Path("scheduled_tasks.txt").exists(), r_dry[:100])
            report("schedule_task (رفض صيغة غلط)", "غير مفهومة" in Tools.schedule_task("كلام فاضي", "echo x"))
            report("schedule_task (رفض كل دقيقة)", "مرفوضة" in Tools.schedule_task("* * * * *", "echo x"))
            del os.environ["SCHEDULE_DRY_RUN"]
        finally:
            try:
                Tools.stop_project("t1")
            except Exception:
                pass
            os.chdir(old_cwd)

        # 🌐 ويب (يحتاج إنترنت — يُتخطى عند غيابه)
        r6 = Tools.web_search("python", 2)
        report("web_search (يحتاج إنترنت)", True if "نتائج البحث" in r6 else None, r6[:100])
        r7 = Tools.browse_web("https://example.com")
        report("browse_web (يحتاج إنترنت)", True if "محتوى الموقع" in r7 or "العنوان" in r7 else None, r7[:100])

    # مُنقذ JSON-كنص (محاكاة سلوك الموديل الصغير)
    fake = "سأنفذ:\n```json\n{\"name\": \"write_file\", \"arguments\": {\"path\": \"x.txt\", \"content\": {\"type\": \"string\", \"value\": \"hi\"}}}\n```"
    rescued = extract_text_tool_calls(fake)
    report("JSON fallback (التقاط من النص)", len(rescued) == 1 and rescued[0]["arguments"].get("content") == "hi", str(rescued)[:100])
    report("JSON fallback (تجاهل غير الأدوات)", extract_text_tool_calls("نص عادي بدون أقواس") == []
           and extract_text_tool_calls('{"name": "nope_tool", "arguments": {}}') == [])

    demo_hist = [("write_file", {"path": "x.txt"}, True, "✅ تم إنشاء وحفظ الملف: `x.txt`"),
                 ("read_file", {"path": "x.txt"}, True, "print('hi')")]
    s = _auto_summary(demo_hist, 2, 1.5, "loop")
    report("auto-summary (ملخص التكرار)", "write_file(x.txt)" in s and "📊" in s, s[:100])

    report("no-action detector (أمر تنفيذي)", _looks_like_action("شغّل مشروع THE WAY OUT") is True)
    report("no-action detector (سؤال)", _looks_like_action("ازاي أشغل المشروع؟") is False)
    report("no-action detector (تحية)", _looks_like_action("سلام عليكم") is False)
    report("goal detector (ويب)", _goal_satisfied("اقرأ موقع https://x.com ولخصه", "browse_web") is True)
    report("goal detector (غير متعلق)", _goal_satisfied("اقرأ موقع https://x.com", "delete_file") is False)
    report("goal summary يحتوي الناتج", "ABC" in _goal_summary("اقرأ موقع", "browse_web", "ABC", 1, 0.5))

    report("intent router (تشغيل)", _match_intent("شغّل مشروع THE WAY OUT") == ("launch_project", {"port": 5000}))
    report("intent router (منفذ)", _match_intent("افحص المنفذ 5000") == ("check_health", {"port": 5000}))
    report("intent router (مرفوض)", _match_intent("اكتب قصيدة عن البحر") is None)

    rslv, _ = resolve_tool_name("read_web")
    report("tool resolver (اسم بديل)", rslv == "browse_web")
    rslv2, _ = resolve_tool_name("browse_wbe")
    report("tool resolver (خطأ إملائي)", rslv2 == "browse_web")
    report("tool resolver (مرفوض)", resolve_tool_name("nope_xyz_123")[0] is None)

    # التقارير النهائية
    brain = AgentBrain()
    ok, detail = brain.check_connection()
    report("Ollama connection (اختياري)", True if ok else None, detail[:120])
    report("frontier (اختياري)", True if frontier_configured() else None,
           f"الموديل: {FRONTIER_MODEL}" if frontier_configured() else "اضبط FRONTIER_API_KEY في .env للإجابات الأقوى")

    print(f"\n{Fore.CYAN}الأدوات المتاحة: {len(TOOLS_SCHEMA)} (full) / {len(TOOLSET_CORE)} (core){Style.RESET_ALL}")
    print(f"{Fore.CYAN}النتيجة: {passed} ناجح ✅ | {failed} فاشل ❌ | {skipped} متخطى ⏭️{Style.RESET_ALL}")
    return 0 if failed == 0 else 1


# ===========================================================================
# الواجهة الرئيسية
# ===========================================================================
BANNER = """
╔══════════════════════════════════════════════════════════╗
║     🚀  T H E   W A Y   O U T   A G E N T  v2.8         ║
║   There's always a way out — دايماً في طريق للخروج     ║
╚══════════════════════════════════════════════════════════╝
"""


def interactive_loop(brain: AgentBrain, toolset: str) -> None:
    print(Fore.GREEN + BANNER + Style.RESET_ALL)
    print(FIRST_RUN_GREETING + "\n")
    ok, detail = brain.check_connection()
    print(f"{(Fore.GREEN if ok else Fore.RED)}🔌 Ollama: {detail}{Style.RESET_ALL}")
    names = TOOLSET_CORE if toolset == "core" else list(TOOLS_SCHEMA.keys())
    print(f"{Fore.CYAN}🧰 الأدوات: {len(names)} ({toolset}) | 💡 اكتب 'help' للمساعدة — 'exit' للخروج{Style.RESET_ALL}\n")

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
            print(f"الأدوات ({len(names)}): " + ", ".join(names) + "\n")
            continue
        if q.lower() in ("tools", "الأدوات"):
            for n in names:
                print(f"  • {n}: {TOOLS_SCHEMA[n]['description']}")
            print()
            continue
        run_agent(q, brain, toolset=toolset)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="THE WAY OUT Agent v2.0 — مساعد ذكي محلي عبر Ollama",
                                     prog="agent.py")
    parser.add_argument("--once", metavar="QUERY", help="تنفيذ أمر واحد ثم الخروج")
    parser.add_argument("--check", action="store_true", help="فحص ذاتي للأدوات بدون موديل")
    parser.add_argument("--version", action="store_true", help="عرض رقم النسخة")
    parser.add_argument("--list-tools", action="store_true", help="عرض كل الأدوات")
    parser.add_argument("--model", default=OLLAMA_MODEL, help=f"الموديل (افتراضي: {OLLAMA_MODEL})")
    parser.add_argument("--base-url", default=OLLAMA_BASE_URL, help="عنوان Ollama")
    parser.add_argument("--max-steps", type=int, default=AGENT_MAX_STEPS, help="أقصى خطوات لكل أمر")
    parser.add_argument("--toolset", choices=["full", "core"], default=AGENT_TOOLSET if AGENT_TOOLSET in ("full", "core") else "full",
                        help="مجموعة الأدوات (core للموديلات الصغيرة)")
    args = parser.parse_args(argv)

    if args.version:
        print(f"THE WAY OUT Agent v{__version__} (model: {args.model} | tools: {len(TOOLS_SCHEMA)})")
        return 0

    if args.list_tools:
        for n, spec in TOOLS_SCHEMA.items():
            tag = "⭐" if n in TOOLSET_CORE else "  "
            print(f"{tag} {n}: {spec['description']}")
        print(f"\nالمجموع: {len(TOOLS_SCHEMA)} أداة (core = {len(TOOLSET_CORE)})")
        return 0

    if args.check:
        return self_check()

    brain = AgentBrain(model=args.model, base_url=args.base_url)

    if args.once:
        run_agent(args.once, brain, max_steps=args.max_steps, toolset=args.toolset)
        return 0

    interactive_loop(brain, args.toolset)
    for name in list(Tools.RUNNING_PROCESSES.keys()):
        Tools.stop_project(name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
