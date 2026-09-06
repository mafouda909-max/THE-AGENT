# AGENTS.md — قواعد العمل داخل هذا المستودع

## البنية
- `agent.py` — المحرك المحلي (THE WAY OUT Agent): حلقة ReAct + 39 أداة + ذاكرة حقائق.
  **لا يُعاد بناؤه.** أي تطوير عليه يكون إضافياً ومغطى باختبارات.
- `lens_operator/` — طبقة LENS Operator فوق المحرك: سياق، سجل تنفيذ، مراجعة ذاتية،
  تعلّم، ذاكرة مشروع. لا تستبدل المحرك ولا تكرره.
- `lens.py` — نقطة دخول CLI: `python lens.py run "TASK"`.
- `tests/` — `test_tools.py` (المحرك) و `test_lens_operator.py` (الطبقة).

## قواعد إلزامية
1. **محلي أولاً:** لا Cloud، لا Remote Desktop، لا اشتراكات مدفوعة.
2. **مساحة العمل:** أي مسار خارج جذر المستودع = `BLOCKED`.
3. **بوابات بشرية:** النشر، الصرف المالي، حذف البيانات، تغيير secrets،
   `git push`، السياسات الأمنية — كلها تتطلب موافقة صريحة.
4. **لا اختلاق نتائج:** `Unknown ≠ Success` · `Missing ≠ Zero` ·
   `Not tested ≠ Passed` · `Simulated ≠ Real`. غير المتحقق منه يُسجَّل `unknown`.
5. **درجات الأدلة:** fact / observation / learning / hypothesis / pattern /
   proven_pattern. تجربة واحدة **لا** تصير حقيقة.
6. **لا حلقات لانهائية:** `MAX_RETRY` واضح؛ بعده `status = blocked` مع تقرير.
7. **لا أسرار في السجلات:** كل ما يُكتب في Execution Records يمر على `redact()`.

## مصادر الحقيقة (بالترتيب)
`docs/CHANNEL_BRAIN.md` (الأعلى) ← `docs/LENS_UNIFIED.md` ←
`content/EP01/STATUS_HONEST.md` ← `operations/*.md` ← `THE_WAY_OUT_HANDOVER.md`.
الملفات غير الموجودة تُتجاهل بصمت — **لا تخترع محتواها.**

## قبل اعتبار أي عمل مكتملاً
```bash
python3 agent.py --check      # فحص المحرك بدون موديل
python3 -m pytest tests/ -q   # كل الاختبارات
```
