# THE WAY OUT — Local Autonomous AI Agent 🤖

> مهندس برمجي ومساعد ذكي ذاتي التشغيل يعمل **محلياً بالكامل** على جهازك (Windows + Ollama)
> بدون إنترنت إلزامي وبدون اشتراكات مدفوعة.

---

## ⚡ تشغيل سريع (Windows PowerShell)

```powershell
# 1) تأكد أن Ollama شغال وأن الموديل موجود
ollama run qwen2.5-coder:1.5b
# اخرج بـ /bye ثم:

# 2) ادخل مجلد المشروع
cd the_way_out

# 3) ثبّت الاعتماديات (أول مرة فقط)
pip install -r requirements.txt

# 4) شغّل الإيجنت
python agent.py
```

> لو قفلت التيرمينال في أي وقت، بس افتح PowerShell جديد وكرر خطوة 2 + 4 — الجلسة تستأنف فوراً،
> لأن الإيجنت Stateless وكل أوامرك تتنفذ من جديد.

### أوامر سريعة داخل الإيجنت

| الأمر | الوظيفة |
|---|---|
| `اكتب ملف hello.py يطبع السلام عليكم` | إنشاء ملفات |
| `اقرأ الملف app.py` | قراءة ملفات |
| `شغّل مشروع THE WAY OUT` | تشغيل سيرفر محلي على `http://localhost:5000` |
| `اقرأ موقع https://example.com ولخصه` | تصفح الويب |
| `نفّذ أمر dir` | تنفيذ أوامر النظام |
| `افحص المنفذ 5000` | فحص سلامة الخدمات |
| `exit` أو `خروج` | إنهاء |

### أوضاع التشغيل

```powershell
python agent.py                  # الوضع التفاعلي (الافتراضي)
python agent.py --once "اكتب ملف test.txt فيه مرحبا"   # أمر واحد ثم خروج
python agent.py --check          # فحص ذاتي للأدوات بدون الحاجة للموديل
python agent.py --version        # رقم النسخة
```

> 💡 لو الموديل صغير (1.5b) وكتب JSON كنص بدل استدعاء الأدوات: الإيجنت بيلتقطه وينفّذه تلقائياً (v2.2+) — ولو استمرت اللخبطة جرّب الوضع الخفيف `--toolset core`.
> 🔁 ولو الموديل علّق في تكرار نفس الخطوة: الإيجنت بيوقفه بعد 3 مرات ويلخص ما تم تلقائياً (v2.3+).
> 🛡️ ولو الموديل ادّعى التنفيذ بدون أدوات: الإيجنت بيرفض الرد ويطالبه بالتنفيذ الحقيقي (v2.4+).
> 🤖 ولو رفض التنفيذ مرتين: الإيجنت بينفّذ النوايا الآمنة الواضحة مباشرة (تشغيل/فحص منفذ/عرض ملفات) — v2.5+.
> 🧠 والأدوات نفسها متسامحة: لو الموديل كتب باراميتر مشوش الإيجنت بيفسره بدل ما يفشل — ولو فشل 3 مرات بينفذ النية مباشرة (v2.6+).
> 🪟 إصلاح Windows: قالب basic آمن للكونسول + فرض UTF-8 على بايثون الفرعي + رسالة واضحة لو الملف سكربت مش سيرفر (v2.7+).
> 🔤 ولو الموديل غلط في اسم أداة (زي read_web بدل browse_web): الإيجنت بيصحح الاسم تلقائياً — والتحذيرات بتذكّره بالمطلوب الأصلي (v2.8+).

---

## 📦 المتطلبات

| المكوّن | التفاصيل |
|---|---|
| نظام التشغيل | Windows 10/11 + PowerShell |
| Python | 3.10 أو أحدث |
| Ollama | يعمل على `http://localhost:11434` |
| الموديل | `qwen2.5-coder:1.5b` (الحالي — مناسب للأجهزة الضعيفة) / `qwen2.5-coder:7b` عند توفر 16GB+ RAM |
| مكتبات Python | `pip install -r requirements.txt` |

لا توجد مفاتيح سرية (API Keys) مطلوبة — التشغيل محلي 100%.

---

## 🛠️ أدوات الإيجنت (39 أداة — مطابق للماستر برومبت v10)

| المجموعة | الأدوات |
|---|---|
| 📁 ملفات | `write_file` `read_file` `edit_file` `list_directory` `delete_file` `search_files` |
| 💻 نظام | `execute_terminal` `run_python` `install_package` `check_system` |
| 🚀 مشاريع | `create_project` `launch_project` `stop_project` `check_health` `read_logs` `monitor_project` |
| 🌐 ويب | `browse_web` `web_search` (بدون API key) `download_file` `call_api` `scrape_data` |
| 🧠 ذاكرة | `remember` `recall` `list_memories` `forget` (دائمة في `memory.json`) |
| 🔧 أكواد | `analyze_code` `review_code` `explain_code` `find_bugs` `generate_tests` `refactor_code` |
| 🎨 محتوى | `generate_readme` `generate_documentation` `generate_content` |
| 📊 أتمتة | `create_automation` `schedule_task` |
| 🤖 متقدم | `use_frontier_model` (حقيقي بمفتاح مجاني) `battle_models` (محلي/سحابي + تحكيم) `run_agent_team` |

> الأسماء القديمة (`list_files` `read_website` `check_port` `launch_the_way_out` `stop_server`) ما زالت تعمل للتوافق.
> تقرير المطابقة الكامل: [`docs/MASTER_PROMPT_COMPLIANCE.md`](docs/MASTER_PROMPT_COMPLIANCE.md).

---

## ⚙️ الإعدادات (اختياري — ملف `.env`)

انسخ `.env.example` إلى `.env` وعدّل عند الحاجة:

```powershell
copy .env.example .env
```

| المتغير | الافتراضي | الوصف |
|---|---|---|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | عنوان سيرفر Ollama |
| `OLLAMA_MODEL` | `qwen2.5-coder:1.5b` | اسم الموديل |
| `OLLAMA_NUM_CTX` | `8192` | حجم السياق (لاستيعاب البرومبت + 39 أداة) |
| `AGENT_MAX_STEPS` | `8` | أقصى عدد خطوات تفكير لكل أمر |
| `AGENT_TIMEOUT` | `60` | مهلة تنفيذ أوامر التيرمينال (ثانية) |
| `AGENT_TOOLSET` | `full` | مجموعة الأدوات: `full` أو `core` (خفيف) |
| `DEFAULT_PORT` | `5000` | منفذ مشروع THE WAY OUT |
| `MEMORY_FILE` | `memory.json` | ملف الذاكرة الدائمة |
| `FRONTIER_API_KEY` | (فارغ) | مفتاح Frontier المجاني — يفعّل الموديلات القوية |
| `FRONTIER_BASE_URL` | `https://openrouter.ai/api/v1` | مزود Frontier (متوافق مع OpenAI) |
| `FRONTIER_MODEL` | `qwen/...:free` | الموديل السحابي الافتراضي |

---

## 🌐 الموديلات القوية المجانية (اختياري — يُفعّل `use_frontier_model` و `battle_models`)

بدون إعداد: الأداتان تجاوبان بالموديل المحلي مع تنبيه. للتفعيل الحقيقي المجاني (دقيقتين):

**OpenRouter (الأسهل):**
1. اعمل حساب على `https://openrouter.ai` وانسخ مفتاحاً من صفحة Keys.
2. في ملف `.env`:
```
FRONTIER_API_KEY=sk-or-v1-xxx
FRONTIER_MODEL=qwen/qwen-2.5-coder-32b-instruct:free
```
3. جرّب: `اسأل الموديل القوي عن شرح decorators في بايثون`

**بدائل مجانية:**
- **Groq** (الأسرع): مفتاح من `console.groq.com` + `FRONTIER_BASE_URL=https://api.groq.com/openai/v1` + `FRONTIER_MODEL=llama-3.3-70b-versatile`
- **Gemini** (حصة كبيرة): مفتاح من `aistudio.google.com` + `FRONTIER_BASE_URL=https://generativelanguage.googleapis.com/v1beta1/openai` + `FRONTIER_MODEL=gemini-2.0-flash`

**المقارنة:** `قارن بين الموديل المحلي وموديل frontier في شرح الـ closures`
(ويمكن التحديد الصريح: `local:qwen2.5-coder:1.5b` مقابل `frontier:llama-3.3-70b-versatile` — مع تحكيم تلقائي ⚖️)

## ⏰ الجدولة الحقيقية

- **Windows:** `schedule_task("09:30", "python backup.py")` → مهمة يومية حقيقية عبر `schtasks`.
- **Linux/macOS:** تثبيت حقيقي في `crontab` مع نسخة احتياطية (`crontab.backup.txt`).
- **وضع المعاينة الآمن:** `SCHEDULE_DRY_RUN=1` يكتب السطر في `scheduled_tasks.txt` بدون تثبيت.

---

## 🗂️ هيكل المشروع

```
the_way_out/
├── agent.py                 ← الإيجنت الموحد (الملف الرئيسي)
├── requirements.txt
├── .env.example
├── README.md
├── THE_WAY_OUT_HANDOVER.md  ← حزمة التسليم الكاملة
├── docs/
│   ├── ARCHITECTURE.md      ← التصميمات المستقبلية (v1 → v10)
│   └── ROADMAP.md           ← خطة العمل والأولويات
├── scripts/
│   ├── setup.ps1            ← تجهيز البيئة على Windows
│   └── run.ps1              ← تشغيل سريع
└── tests/
    └── test_tools.py        ← اختبارات الأدوات (بدون موديل)
```

---

## 🧪 الاختبار بدون موديل

```powershell
python agent.py --check
python -m pytest tests/ -v
```

---

## 🗺️ الخطوات الجاية (حسب الأولوية)

1. **[قصوى]** تشغيل `agent.py` والتأكد من استجابة الموديل للأوامر المحلية.
2. **[عالية]** اختبار المهارات الحية: تشغيل المشروع، إنشاء ملفات، سحب موقع ويب.
3. **[متوسطة]** أتمتة تصفح متقدمة (Playwright) لمواقع العمل الحر.
4. **[لاحقة]** واجهة ويب (FastAPI + Streaming UI) بدل سطر الأوامر فقط.

التفاصيل الكاملة في [`THE_WAY_OUT_HANDOVER.md`](THE_WAY_OUT_HANDOVER.md) و [`docs/ROADMAP.md`](docs/ROADMAP.md).

---

## 🛡️ الأمان

- ⛔ حظر تلقائي للأوامر التدميرية (`rm -rf /`, `format`, `del /f /s /q C:\*` ... إلخ).
- 🔑 المتغيرات الحساسة تُعزل في `.env` ولا تُرفع أبداً على Git.
- 🏠 كل التنفيذ محلي — لا تُرسل بياناتك لأي سيرفر خارجي إلا عند استخدام `read_website` صراحةً.
