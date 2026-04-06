from __future__ import annotations

import json
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import dedent

from app.judge.sandbox import SandboxExecutionError, SandboxRunResult, dump_json, get_sandbox
from app.models import Question, TestCase


DOCKER_PATH = "/workspace/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Q03_CALENDAR = "    October 1949\nSu Mo Tu We Th Fr Sa\n                   1\n 2  3  4  5  6  7  8\n 9 10 11 12 13 14 15\n16 17 18 19 20 21 22\n23 24 25 26 27 28 29\n30 31\n"


@dataclass
class DynamicRunResult:
    passed: bool
    actual_output: str | None
    expected_output: str | None
    error: str | None
    execution_time_ms: float


def _write_tree(root: Path, tree: dict[str, str] | None) -> None:
    for relative_path, content in (tree or {}).items():
        file_path = root / relative_path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")


def _write_executable(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _normalize_output(text: str) -> str:
    return text.replace("\r\n", "\n")


def _collect_expected_files(root: Path, expected_files: dict[str, str] | None) -> list[str]:
    mismatches: list[str] = []
    for relative_path, expected in (expected_files or {}).items():
        target = root / relative_path
        if not target.exists():
            mismatches.append(f"missing file: {relative_path}")
            continue
        actual = target.read_text(encoding="utf-8")
        if actual != expected:
            mismatches.append(f"file content mismatch: {relative_path}")
    return mismatches


def _prepare_command_workspace(workspace: Path, question: Question, case: TestCase) -> None:
    _write_tree(workspace, case.input_files_json)
    bin_dir = workspace / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    if question.id == "Q02":
        _write_executable(
            bin_dir / "ssh",
            dedent(
                """\
                #!/usr/bin/env bash
                printf '%s\n' "$*" > "$WORKSPACE_ROOT/ssh_invocation.log"
                exit 0
                """
            ),
        )
    elif question.id == "Q03":
        _write_executable(
            bin_dir / "who",
            dedent(
                """\
                #!/usr/bin/env bash
                if [ "$1" = "-b" ] || [ "$1" = "--boot" ]; then
                  printf '%s\n' '         system boot  2024-10-01 08:00'
                else
                  /usr/bin/who "$@"
                fi
                """
            ),
        )
        _write_executable(
            bin_dir / "uname",
            dedent(
                """\
                #!/usr/bin/env bash
                if [ "$1" = "-r" ]; then
                  printf '%s\n' '6.8.0-autograder'
                else
                  /usr/bin/uname "$@"
                fi
                """
            ),
        )
        _write_executable(
            bin_dir / "date",
            dedent(
                """\
                #!/usr/bin/env bash
                if [ "$1" = '+%Y|%m|%d_%H:%M' ]; then
                  printf '%s\n' '2024|10|01_08:00'
                else
                  /usr/bin/date "$@"
                fi
                """
            ),
        )
        _write_executable(
            bin_dir / "cal",
            "#!/usr/bin/env bash\n"
            "if [ \"$#\" -eq 2 ] && [ \"$1\" = \"10\" ] && [ \"$2\" = \"1949\" ]; then\n"
            "cat <<'EOF'\n"
            f"{Q03_CALENDAR.rstrip()}\n"
            "EOF\n"
            "elif [ \"$#\" -eq 2 ] && [ \"$1\" = \"1949\" ] && [ \"$2\" = \"10\" ]; then\n"
            "cat <<'EOF'\n"
            f"{Q03_CALENDAR.rstrip()}\n"
            "EOF\n"
            "else\n"
            "  /usr/bin/cal \"$@\"\n"
            "fi\n",
        )
    elif question.id == "Q05":
        _write_executable(
            bin_dir / "ls",
            dedent(
                """\
                #!/usr/bin/env bash
                if [ "$1" = "-ali" ] || [ "$1" = "-ail" ] || [ "$1" = "-lai" ] || [ "$1" = "-lia" ]; then
                  cat <<'EOF'
                total 5
                11 drwxr-xr-x 3 student student 4096 .
                12 drwxr-xr-x 3 student student 4096 ..
                13 -rw-r--r-- 1 student student    2 .hidden
                14 -rw-r--r-- 1 student student   12 week5_11.txt
                15 -rw-r--r-- 1 student student   12 week5_12.txt
                16 -rw-r--r-- 1 student student    8 week5_14.log
                17 drwxr-xr-x 2 student student 4096 week5_14_dest
                18 -rw-r--r-- 1 student student   10 week5_15.log
                EOF
                else
                  /usr/bin/ls "$@"
                fi
                """
            ),
        )
    elif question.id == "Q06":
        chmod_target = workspace / "week6_2.dat"
        if chmod_target.exists():
            chmod_target.chmod(0o754)
        _write_executable(
            bin_dir / "vi",
            "#!/usr/bin/env bash\n"
            "args=\"$*\"\n"
            "printf '%s\\n' \"$args\" > \"$WORKSPACE_ROOT/vi_invocation.log\"\n"
            "if [[ \"$args\" != *\"week6_1.txt\"* ]] || [[ \"$args\" != *\"line22222222\"* ]] || [[ \"$args\" != *\":5d\"* ]] || [[ \"$args\" != *\"+x\"* ]]; then\n"
            "  printf '%s\\n' 'vi command arguments not accepted' >&2\n"
            "  exit 2\n"
            "fi\n"
            "python3 - <<'PY'\n"
            "from pathlib import Path\n"
            "target = Path('week6_1.txt')\n"
            "lines = target.read_text(encoding='utf-8').splitlines()\n"
            "lines.insert(1, '[line22222222]')\n"
            "if len(lines) >= 5:\n"
            "    del lines[4]\n"
            "target.write_text('\\n'.join(lines) + '\\n', encoding='utf-8')\n"
            "PY\n",
        )
        _write_executable(bin_dir / "vim", (bin_dir / "vi").read_text(encoding="utf-8"))
    return None


def _build_submission_script(question: Question, submitted_code: str) -> str:
    if question.question_type == "script":
        body = submitted_code.rstrip("\n") + "\n"
    else:
        body = submitted_code.rstrip() + "\n"
    return dedent(
        f"""\
        #!/usr/bin/env bash
        set -euo pipefail
        export LC_ALL=C.UTF-8
        {body}
        """
    )


def _verify_shell_case(
    question: Question,
    case: TestCase,
    workspace: Path,
    run_result: SandboxRunResult,
    submitted_code: str,
) -> DynamicRunResult:
    stdout = _normalize_output(run_result.stdout)
    stderr = _normalize_output(run_result.stderr)
    metadata = question.metadata_json
    if run_result.timed_out:
        return DynamicRunResult(False, stdout, case.expected_output, "执行超时。", run_result.execution_time_ms)
    if run_result.exit_code != 0:
        return DynamicRunResult(False, stdout or stderr, case.expected_output, stderr or f"命令退出码为 {run_result.exit_code}", run_result.execution_time_ms)

    if question.id == "Q02":
        invocation = (workspace / "ssh_invocation.log").read_text(encoding="utf-8").strip() if (workspace / "ssh_invocation.log").exists() else ""
        accepted = metadata.get("accepted_invocations", [])
        required_exit = metadata.get("required_exit_command", "exit")
        command_lines = [line.strip() for line in submitted_code.splitlines() if line.strip()]
        has_expected_exit = len(command_lines) >= 2 and command_lines[-1] == required_exit
        passed = invocation in accepted and has_expected_exit
        expected = "ssh user01@127.0.0.1\nexit"
        actual = "\n".join(command_lines) if command_lines else (invocation or stdout)
        if invocation not in accepted:
            error = "ssh 目标或用户不正确。"
        elif not has_expected_exit:
            error = "登录成功后需要执行 exit 退出登录。"
        else:
            error = None
        return DynamicRunResult(passed, actual, expected, error, run_result.execution_time_ms)

    if question.id == "Q04":
        expected_output = metadata["expected_output_template"].format(root=str(workspace), child=str(workspace / "week5_6"))
        passed = stdout == expected_output
        return DynamicRunResult(passed, stdout, expected_output, None if passed else "目录切换或文件合并结果不正确。", run_result.execution_time_ms)

    if question.id == "Q05":
        mismatches = _collect_expected_files(workspace, case.expected_files_json)
        for relative_path in metadata.get("absent_paths", []):
            if (workspace / relative_path).exists():
                mismatches.append(f"unexpected path exists: {relative_path}")
        expected_output = case.expected_output or ""
        if stdout != expected_output:
            mismatches.append("stdout mismatch")
        error = None if not mismatches else "；".join(mismatches)
        return DynamicRunResult(not mismatches, stdout, expected_output, error, run_result.execution_time_ms)

    if question.id == "Q06":
        vi_log = (workspace / "vi_invocation.log").read_text(encoding="utf-8").strip() if (workspace / "vi_invocation.log").exists() else ""
        expected_vi_markers = metadata.get("required_vi_markers", [])
        expected_mode = metadata.get("expected_mode")
        actual_mode = oct((workspace / "week6_2.dat").stat().st_mode & 0o777)[2:]
        expected_files = _collect_expected_files(workspace, case.expected_files_json)
        for marker in expected_vi_markers:
            if marker not in vi_log:
                expected_files.append(f"missing vi marker: {marker}")
        if actual_mode != expected_mode:
            expected_files.append(f"mode mismatch: expected {expected_mode}, got {actual_mode}")
        actual = json.dumps({"vi_invocation": vi_log, "chmod_mode": actual_mode}, ensure_ascii=False)
        expected = json.dumps({"required_vi_markers": expected_vi_markers, "chmod_mode": expected_mode}, ensure_ascii=False)
        return DynamicRunResult(not expected_files, actual, expected, None if not expected_files else "；".join(expected_files), run_result.execution_time_ms)

    expected_output = case.expected_output or ""
    mismatches = _collect_expected_files(workspace, case.expected_files_json)
    if stdout != expected_output:
        mismatches.append("stdout mismatch")
    error = None if not mismatches else "；".join(mismatches)
    actual = stdout if stdout else (stderr or None)
    return DynamicRunResult(not mismatches, actual, expected_output, error, run_result.execution_time_ms)


def run_shell_case(question: Question, case: TestCase, submitted_code: str) -> DynamicRunResult:
    sandbox = get_sandbox()
    with TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        _prepare_command_workspace(workspace, question, case)
        submission_script = workspace / "submission.sh"
        _write_executable(submission_script, _build_submission_script(question, submitted_code))
        path_value = f"{workspace / 'bin'}:{os.environ.get('PATH', '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin')}"
        workspace_root = str(workspace)
        if sandbox.backend_name == "docker":
            path_value = DOCKER_PATH
            workspace_root = "/workspace"
        env = {"WORKSPACE_ROOT": workspace_root, "PATH": path_value}
        try:
            run_result = sandbox.run(
                workspace,
                ["/bin/bash", "submission.sh"],
                stdin=case.input_data or "",
                env=env,
                timeout_ms=question.time_limit_ms,
                memory_limit_mb=question.memory_limit_mb,
            )
        except SandboxExecutionError as exc:
            return DynamicRunResult(False, None, case.expected_output, str(exc), 0.0)
        return _verify_shell_case(question, case, workspace, run_result, submitted_code)


def run_python_case(question: Question, case: TestCase, submitted_code: str) -> DynamicRunResult:
    sandbox = get_sandbox()
    with TemporaryDirectory() as tmp:
        workspace = Path(tmp)
        payload = {
            "code": submitted_code,
            "entry_function": question.metadata_json.get("entry_function", "solve"),
            "args": case.call_args_json or [],
        }
        dump_json(workspace / "payload.json", payload)
        runner = dedent(
            """\
            import json
            import sys
            import time
            from pathlib import Path

            payload = json.loads(Path("payload.json").read_text(encoding="utf-8"))
            namespace = {"__builtins__": {"len": len, "range": range, "sum": sum, "min": min, "max": max, "abs": abs}}
            started = time.perf_counter()
            try:
                exec(payload["code"], namespace, namespace)
                func = namespace.get(payload["entry_function"])
                if not callable(func):
                    result = {"actual_output": None, "error": f"未找到可调用函数: {payload['entry_function']}"}
                else:
                    result = {"actual_output": str(func(*payload["args"])), "error": None}
            except Exception as exc:  # noqa: BLE001
                result = {"actual_output": None, "error": str(exc)}
            result["execution_time_ms"] = (time.perf_counter() - started) * 1000
            print(json.dumps(result, ensure_ascii=False))
            """
        )
        _write_executable(workspace / "runner.py", runner)
        path_value = f"{workspace / 'bin'}:{os.environ.get('PATH', '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin')}"
        if sandbox.backend_name == "docker":
            path_value = DOCKER_PATH
        env = {"PATH": path_value}
        python_cmd = question.metadata_json.get("python_command", "python3")
        try:
            run_result = sandbox.run(
                workspace,
                [python_cmd, "runner.py"],
                env=env,
                timeout_ms=question.time_limit_ms,
                memory_limit_mb=max(question.memory_limit_mb, 256),
            )
        except SandboxExecutionError as exc:
            return DynamicRunResult(False, None, case.expected_output, str(exc), 0.0)

        if run_result.timed_out:
            return DynamicRunResult(False, None, case.expected_output, "执行超时。", run_result.execution_time_ms)
        if run_result.exit_code != 0:
            message = run_result.stderr.strip() or run_result.stdout.strip() or f"子进程退出码为 {run_result.exit_code}"
            return DynamicRunResult(False, None, case.expected_output, message, run_result.execution_time_ms)
        try:
            payload = json.loads(run_result.stdout)
        except json.JSONDecodeError:
            message = run_result.stdout.strip() or "子进程返回了无法解析的结果。"
            return DynamicRunResult(False, run_result.stdout, case.expected_output, message, run_result.execution_time_ms)

        actual = payload.get("actual_output")
        error = payload.get("error")
        passed = error is None and actual == case.expected_output
        return DynamicRunResult(
            passed=passed,
            actual_output=actual,
            expected_output=case.expected_output,
            error=error if error is not None else (None if passed else "返回值与预期不一致。"),
            execution_time_ms=float(payload.get("execution_time_ms", run_result.execution_time_ms)),
        )
