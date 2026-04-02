import ast
import time
from dataclasses import dataclass
from typing import Any


@dataclass
class ApiRunResult:
    """执行一条 API 题测试用例后的结果。

    `actual_output` 表示函数真实返回值，
    `error` 表示执行过程中是否报错，
    `execution_time_ms` 表示运行耗时，单位是毫秒。
    """

    actual_output: str | None
    error: str | None
    execution_time_ms: float


FORBIDDEN_IMPORTS = {"os", "sys", "subprocess", "socket", "ctypes", "pathlib", "shutil"}
FORBIDDEN_CALLS = {"eval", "exec", "compile", "__import__", "open"}


def _check_python_safety(code: str) -> list[str]:
    """在真正执行代码前，先做一轮 Python 静态安全检查。

    这里不是运行代码，而是先把代码解析成语法树（AST），
    再去检查里面有没有：
    - 被禁止导入的模块
    - 被禁止调用的内置函数

    这样可以在执行前尽早挡住明显危险的代码。
    """

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
    """执行 API 类型题目的用户代码。

    整个流程是：
    1. 先做安全检查
    2. 把代码放进一个受限命名空间里执行
    3. 找到约定好的入口函数
    4. 用测试用例参数去调用这个函数
    5. 把返回值、异常信息、耗时整理后返回
    """

    issues = _check_python_safety(code)
    if issues:
        return ApiRunResult(actual_output=None, error="; ".join(issues), execution_time_ms=0.0)
    started = time.perf_counter()
    # 这里只开放极少量安全的内置函数。
    # 目的不是让用户代码“什么都能做”，而是只允许它完成题目要求的纯计算逻辑，
    # 尽量减少访问文件系统、系统命令、网络等危险能力的机会。
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
