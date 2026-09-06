# 🧭 LENS Operator v0.1

Local Autonomous Project Operator — طبقة تشغيل فوق `agent.py`، مش بديل عنه.

```
CHANNEL BRAIN → LENS → LENS OPERATOR → LOCAL AGENT → TOOLS → EXECUTION
    → SELF REVIEW → LEARNING → PROJECT MEMORY → NEXT EXECUTION
```

## الاستخدام

```bash
python lens.py run "راجع حالة المشروع ونفذ أهم مهمة معلقة"
python lens.py run "أنشئ ملف اختبار" --no-tests   # تخطي pytest
python lens.py run "publish episode" --approve     # منح الموافقة مسبقاً
python lens.py status      # آخر تنفيذ + إحصاء الذاكرة
python lens.py history     # سجل التنفيذات
python lens.py memory      # التعلّمات والإخفاقات والأنماط
python lens.py review      # مراجعة آخر تنفيذ (JSON)
```

## دورة التنفيذ

| المرحلة | الملف | ماذا يحدث |
|---|---|---|
| Load Context | `context.py` | حالة المشروع + Git + مصادر الحقيقة + ذاكرة ذات صلة |
| Plan | `operator.py` | خطة صريحة تُسجَّل في السجل |
| Execute | `operator.py` | يستدعي `agent.run_agent` (المحرك الحالي) مع حقن السياق |
| Failure loop | `operator.py` | تشخيص → إعادة محاولة (`MAX_RETRY=2`) → `blocked` |
| Test | `operator.py` | `pytest tests/ -q` وتسجيل النتيجة الحقيقية |
| Self-Review | `review.py` | 9 أسئلة إلزامية + درجة من 100 + ملاحظات |
| Learn + Persist | `memory.py` | تعلّمات/إخفاقات/أنماط بدرجات ثقة |
| Report | `record.py` | تقرير أمين بحالة صريحة |

## الحالات
`completed` · `failed` · `blocked` · `needs_approval` · `unknown`

## طبقات الأدلة
`hypothesis → observation → learning → pattern → proven_pattern → fact`
الترقية تلقائية بالتكرار (نمط عند مشاهدتين، مثبت عند ثلاث) — **لا ترقية بلا دليل**.

## الأمان
- خارج مساحة العمل = `BLOCKED` قبل أي تنفيذ.
- بوابات بشرية: نشر، صرف، حذف بيانات، secrets، `git push`، سياسات أمنية.
- `redact()` على كل ما يُكتب في السجلات — لا مفاتيح ولا كلمات سر.
- Git للقراءة فقط (`status` / `diff`) — لا `push` تلقائي.

## التخزين
```
memory/
├── project_state/state.json
├── executions/EX-000001.json     # السجل الكامل
├── executions.jsonl              # فهرس سريع
├── learnings.jsonl  failures.jsonl  decisions.jsonl
└── patterns.jsonl   proven_patterns.jsonl
```
`memory/` خارج Git افتراضياً (أدلة محلية).
