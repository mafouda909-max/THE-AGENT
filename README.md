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

## 🛠️ أدوات الإيجنت (Tools)

| الأداة | الوصف |
|---|---|
| `execute_terminal` | تنفيذ أوامر النظام (مع حظر الأوامر التدميرية) |
| `write_file` | إنشاء وتعديل الملفات |
| `read_file` | قراءة الملفات |
| `list_files` | عرض محتويات مجلد |
| `launch_the_way_out` | تشغيل سيرفر محلي تجريبي للمشروع |
| `read_website` | سحب وتلخيص محتوى أي موقع |
| `check_port` | فحص هل منفذ/خدمة شغالة أم لا |

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
| `AGENT_MAX_STEPS` | `5` | أقصى عدد خطوات تفكير لكل أمر |
| `AGENT_TIMEOUT` | `60` | مهلة تنفيذ أوامر التيرمينال (ثانية) |
| `DEFAULT_PORT` | `5000` | منفذ مشروع THE WAY OUT |

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
