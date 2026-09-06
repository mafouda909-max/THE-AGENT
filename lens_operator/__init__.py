"""LENS Operator — طبقة تشغيل محلية فوق THE WAY OUT Agent.

Command → Context → Plan → Execute → Test → Self-Review → Learn → Memory → Report
"""

__version__ = "0.1.0"

from .memory import ProjectMemory, Evidence  # noqa: F401
from .record import ExecutionRecord, Status  # noqa: F401
from .context import ExecutionContext, load_context  # noqa: F401
from .review import self_review  # noqa: F401
from .operator import LensOperator  # noqa: F401
