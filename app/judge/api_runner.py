import ast
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class ApiRunResult:
    actual_output: str | None
    error: str | None
    execution_time_ms: float


FORBIDDEN_IMPORTS = {"os", "sys", "subprocess", "socket", "ctypes", "pathlib", "shutil"}
FORBIDDEN_CALLS = {"eval", "exec", "compile", "__import__", "open"}


def _check_python_safety(code: str) -> list[str]:
    tree = ast.parse(code)
    issues: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [alias.name.split(".")[0] for alias in node.names]
            blocked = [name for name in names if name in FORBIDDEN_IMPORTS]
            if blocked:
                issues.append(f"禁止导入模块: {', '.join(blocked)}")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
            issues.append(f"禁止调用函数: {node.func.id}")
    return issues


def run_api_case(code: str, entry_function: str, args: list[Any]) -> ApiRunResult:
    issues = _check_python_safety(code)
    if issues:
        return ApiRunResult(actual_output=None, error="; ".join(issues), execution_time_ms=0.0)
    started = time.perf_counter()
    namespace: dict[str, Any] = {"__builtins__": {"len": len, "range": range, "sum": sum, "min": min, "max": max, "abs": abs}}
    try:
        exec(code, namespace, namespace)
        func = namespace.get(entry_function)
        if not callable(func):
            return ApiRunResult(actual_output=None, error=f"未找到可调用函数: {entry_function}", execution_time_ms=0.0)
        result = func(*args)
        elapsed = (time.perf_counter() - started) * 1000
        return ApiRunResult(actual_output=str(result), error=None, execution_time_ms=elapsed)
    except Exception as exc:  # noqa: BLE001
        elapsed = (time.perf_counter() - started) * 1000
        return ApiRunResult(actual_output=None, error=str(exc), execution_time_ms=elapsed)
