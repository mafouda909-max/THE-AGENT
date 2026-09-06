"""CLI: `lens run "TASK"` — الأولوية في v0.1 لأمر التشغيل."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .memory import ProjectMemory
from .operator import LensOperator


def _memory(ws: Path) -> ProjectMemory:
    return ProjectMemory(ws / "memory")


def cmd_run(args) -> int:
    ws = Path(args.workspace).resolve()

    def approver(reason, command):
        if args.approve:
            return True
        print(f"⏸️  موافقة بشرية مطلوبة: {reason}")
        if not sys.stdin.isatty():
            return False
        return input("توافق؟ [y/N] ").strip().lower() in ("y", "yes", "نعم")

    op = LensOperator(workspace=ws, memory=_memory(ws), approver=approver,
                      run_tests=not args.no_tests)
    record = op.run(args.task, dry_run=args.dry_run)
    print()
    print(record.report())
    print(f"\n📁 Execution record: memory/executions/{record.execution_id}.json")
    return 0 if record.status == "completed" else 1


def cmd_status(args) -> int:
    ws = Path(args.workspace).resolve()
    mem = _memory(ws)
    state, stats = mem.project_state(), mem.stats()
    print(f"LENS Operator v{__version__} — {ws}")
    print(f"آخر تنفيذ: {state.get('last_execution', '(لا يوجد)')} "
          f"[{state.get('last_status', 'n/a')}]")
    print(f"آخر أمر: {state.get('last_command', '-')}")
    print("الذاكرة: " + ", ".join(f"{k}={v}" for k, v in stats.items()))
    return 0


def cmd_memory(args) -> int:
    mem = _memory(Path(args.workspace).resolve())
    for kind in ProjectMemory.KINDS:
        items = mem.all_items(kind)
        if not items:
            continue
        print(f"\n## {kind} ({len(items)})")
        for it in items[-args.limit:]:
            print(f"  [{it.get('tier')}] x{it.get('occurrences', 1)} "
                  f"{it.get('text')}  ({it.get('source_execution')})")
    return 0


def cmd_history(args) -> int:
    mem = _memory(Path(args.workspace).resolve())
    rows = mem.executions(limit=args.limit)
    if not rows:
        print("(لا تنفيذات سابقة)")
        return 0
    for e in rows:
        print(f"{e.get('execution_id')}  {str(e.get('status')):14}  "
              f"tests={e.get('tests')}  score={e.get('score')}  "
              f"{str(e.get('command'))[:60]}")
    return 0


def cmd_review(args) -> int:
    mem = _memory(Path(args.workspace).resolve())
    ex_id = args.execution or (mem.executions(limit=1) or [{}])[0].get("execution_id")
    if not ex_id:
        print("(لا تنفيذات)")
        return 1
    rec = mem.load_execution(ex_id)
    if not rec:
        print(f"❌ لا يوجد سجل {ex_id}")
        return 1
    print(json.dumps(rec.get("review", {}), ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="lens",
                                description="LENS Operator — Local Autonomous Project Operator")
    p.add_argument("--version", action="version", version=f"LENS Operator v{__version__}")
    p.add_argument("-w", "--workspace", default=".", help="مساحة العمل (افتراضي: .)")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help='تنفيذ أمر: lens run "TASK"')
    r.add_argument("task")
    r.add_argument("--dry-run", action="store_true", help="بناء السياق بدون تنفيذ")
    r.add_argument("--no-tests", action="store_true", help="تخطي تشغيل الاختبارات")
    r.add_argument("--approve", action="store_true", help="منح الموافقة البشرية مسبقاً")
    r.set_defaults(func=cmd_run)

    s = sub.add_parser("status", help="حالة المشروع والذاكرة")
    s.set_defaults(func=cmd_status)

    m = sub.add_parser("memory", help="عرض ذاكرة المشروع")
    m.add_argument("--limit", type=int, default=10)
    m.set_defaults(func=cmd_memory)

    h = sub.add_parser("history", help="سجل التنفيذات")
    h.add_argument("--limit", type=int, default=20)
    h.set_defaults(func=cmd_history)

    v = sub.add_parser("review", help="مراجعة تنفيذ")
    v.add_argument("execution", nargs="?")
    v.set_defaults(func=cmd_review)
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    # -w يأتي قبل الأمر الفرعي؛ نضمن وجوده دائماً
    if not hasattr(args, "workspace"):
        args.workspace = "."
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
