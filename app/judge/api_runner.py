import ast
from dataclasses import dataclass
from app.judge.dynamic_runner import python_judge_mode, run_python_case
from app.models import Question, TestCase


@dataclass
class ApiRunResult:
    actual_output: str | None
    error: str | None
    execution_time_ms: float


FORBIDDEN_IMPORTS = {"os", "sys", "subprocess", "socket", "ctypes", "pathlib", "shutil"}
FORBIDDEN_CALLS = {"eval", "exec", "compile", "__import__", "open"}


def _check_python_safety(code: str, forbidden_imports: set[str] | None = None, forbidden_calls: set[str] | None = None) -> list[str]:
    """在真正执行代码前，先做一轮 Python 静态安全检查。"""

    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [f"语法错误: {exc.msg}"]
    blocked_imports = forbidden_imports if forbidden_imports is not None else FORBIDDEN_IMPORTS
    blocked_calls = forbidden_calls if forbidden_calls is not None else FORBIDDEN_CALLS
    issues: list[str] = []
    for node in ast.walk(tree):
        # API 题允许提交函数实现，但不允许借助系统能力逃逸出题目环境。
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [alias.name.split(".")[0] for alias in node.names]
            blocked = [name for name in names if name in blocked_imports]
            if blocked:
                issues.append(f"禁止导入模块: {', '.join(blocked)}")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in blocked_calls:
            issues.append(f"禁止调用函数: {node.func.id}")
    return issues


def _forbidden_imports_for_question(question: Question, case: TestCase) -> set[str]:
    metadata = question.metadata_json or {}
    configured = metadata.get("forbidden_modules")
    if configured is not None:
        return set(configured)
    blocked = set(FORBIDDEN_IMPORTS)
    if python_judge_mode(question, case) == "stdin":
        blocked.discard("sys")
    return blocked


def run_api_case(question: Question, case: TestCase, code: str) -> ApiRunResult:
    """执行 API 题。

    这里仍然保留原本的 AST 静态安全检查，
    但实际运行改成走统一的沙盒执行器。
    """

    metadata = question.metadata_json or {}
    issues = _check_python_safety(code, _forbidden_imports_for_question(question, case), set(metadata.get("forbidden_functions", FORBIDDEN_CALLS)))
    if issues:
        return ApiRunResult(actual_output=None, error="; ".join(issues), execution_time_ms=0.0)

    result = run_python_case(question, case, code)
    return ApiRunResult(
        actual_output=result.actual_output,
        error=result.error,
        execution_time_ms=result.execution_time_ms,
    )
