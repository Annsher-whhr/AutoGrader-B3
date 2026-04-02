import ast
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
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

RUNNER_SCRIPT = """
import json
import sys
import time
from pathlib import Path


def main() -> int:
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    namespace = {
        "__builtins__": {
            "len": len,
            "range": range,
            "sum": sum,
            "min": min,
            "max": max,
            "abs": abs,
        }
    }
    started = time.perf_counter()
    try:
        exec(payload["code"], namespace, namespace)
        func = namespace.get(payload["entry_function"])
        if not callable(func):
            result = {
                "actual_output": None,
                "error": f"未找到可调用函数: {payload['entry_function']}",
                "execution_time_ms": 0.0,
            }
        else:
            actual = func(*payload["args"])
            elapsed = (time.perf_counter() - started) * 1000
            result = {
                "actual_output": str(actual),
                "error": None,
                "execution_time_ms": elapsed,
            }
    except Exception as exc:
        elapsed = (time.perf_counter() - started) * 1000
        result = {
            "actual_output": None,
            "error": str(exc),
            "execution_time_ms": elapsed,
        }
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
""".strip()


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


def run_api_case(code: str, entry_function: str, args: list[Any], timeout_ms: int = 2000) -> ApiRunResult:
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
    try:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            payload_path = tmp_path / "payload.json"
            runner_path = tmp_path / "runner.py"
            payload_path.write_text(
                json.dumps({"code": code, "entry_function": entry_function, "args": args}, ensure_ascii=False),
                encoding="utf-8",
            )
            runner_path.write_text(RUNNER_SCRIPT, encoding="utf-8")
            completed = subprocess.run(
                [sys.executable, str(runner_path), str(payload_path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                cwd=tmp,
                timeout=max(timeout_ms / 1000, 0.1),
                check=False,
            )
    except subprocess.TimeoutExpired:
        return ApiRunResult(actual_output=None, error="执行超时。", execution_time_ms=float(timeout_ms))
    except Exception as exc:  # noqa: BLE001
        return ApiRunResult(actual_output=None, error=str(exc), execution_time_ms=0.0)

    if completed.returncode != 0:
        message = completed.stderr.strip() or completed.stdout.strip() or "子进程执行失败。"
        return ApiRunResult(actual_output=None, error=message, execution_time_ms=0.0)

    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError:
        message = completed.stdout.strip() or "子进程返回了无法解析的结果。"
        return ApiRunResult(actual_output=None, error=message, execution_time_ms=0.0)

    return ApiRunResult(
        actual_output=payload.get("actual_output"),
        error=payload.get("error"),
        execution_time_ms=float(payload.get("execution_time_ms", 0.0)),
    )
