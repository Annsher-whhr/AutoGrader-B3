import re
import shlex

from app.schemas import StaticIssue


DANGEROUS_TOKENS = {"rm", "sudo", "shutdown", "reboot", "mkfs", "curl", "wget", "nc", "netcat", "powershell", "cmd.exe"}
FORBIDDEN_CHARS = ["&&", "||", ";", ">", ">>", "<", "`", "$(", "${", "|&"]


def scan_shell_code(submitted_code: str, allowed_commands: list[str]) -> list[StaticIssue]:
    issues: list[StaticIssue] = []
    for token in FORBIDDEN_CHARS:
        if token in submitted_code:
            issues.append(StaticIssue(code="FORBIDDEN_SHELL_SYNTAX", message=f"检测到危险 shell 语法: {token}"))
    lines = [line.strip() for line in submitted_code.splitlines() if line.strip()]
    if len(lines) > 20:
        issues.append(StaticIssue(code="TOO_MANY_LINES", message="命令行数异常，疑似非题目要求答案。"))
    for line in lines:
        try:
            parts = shlex.split(line)
        except ValueError:
            issues.append(StaticIssue(code="PARSE_ERROR", message=f"命令无法解析: {line}"))
            continue
        if not parts:
            continue
        command = parts[0]
        if command in DANGEROUS_TOKENS:
            issues.append(StaticIssue(code="DANGEROUS_COMMAND", message=f"检测到危险命令: {command}"))
        if allowed_commands and command not in allowed_commands:
            issues.append(StaticIssue(code="COMMAND_NOT_ALLOWED", message=f"命令不在白名单中: {command}"))
        if re.search(r"\.\.[\\/]", line):
            issues.append(StaticIssue(code="PATH_ESCAPE", message="检测到越界路径访问。"))
    return issues


def scan_script_code(submitted_code: str) -> list[StaticIssue]:
    issues = scan_shell_code(submitted_code, [])
    lowered = submitted_code.lower()
    if "while true" in lowered or "while :" in lowered:
        issues.append(StaticIssue(code="POSSIBLE_INFINITE_LOOP", message="检测到疑似死循环。"))
    return issues
