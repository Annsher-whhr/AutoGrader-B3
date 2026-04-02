import re
import shlex

from app.schemas import StaticIssue


DANGEROUS_TOKENS = {"rm", "sudo", "shutdown", "reboot", "mkfs", "curl", "wget", "nc", "netcat", "powershell", "cmd.exe"}
FORBIDDEN_CHARS = ["&&", "||", ";", ">", ">>", "<", "`", "$(", "${", "|&"]


def scan_shell_code(submitted_code: str, allowed_commands: list[str]) -> list[StaticIssue]:
    """对 shell 答案做静态安全检查。

    这里的“静态”意思是：
    只检查文本内容本身，不真正执行用户提交的命令。

    这样做的目的，是先挡掉一批明显危险的内容，
    例如重定向、命令拼接、路径越界、危险命令等。
    """

    issues: list[StaticIssue] = []
    for token in FORBIDDEN_CHARS:
        if token in submitted_code:
            issues.append(StaticIssue(code="FORBIDDEN_SHELL_SYNTAX", message=f"dangerous shell syntax detected: {token}"))
    # 这里的题目主要是课堂练习题，答案通常应该是很短的命令序列。
    # 如果行数特别多，往往说明提交内容已经偏离题意，所以直接记一个问题。
    lines = [line.strip() for line in submitted_code.splitlines() if line.strip()]
    if len(lines) > 20:
        issues.append(StaticIssue(code="TOO_MANY_LINES", message="too many command lines for this question"))
    for line in lines:
        try:
            parts = shlex.split(line)
        except ValueError:
            issues.append(StaticIssue(code="PARSE_ERROR", message=f"unable to parse command: {line}"))
            continue
        if not parts:
            continue
        command = parts[0]
        if command in DANGEROUS_TOKENS:
            issues.append(StaticIssue(code="DANGEROUS_COMMAND", message=f"dangerous command detected: {command}"))
        if allowed_commands and command not in allowed_commands:
            issues.append(StaticIssue(code="COMMAND_NOT_ALLOWED", message=f"command is not allowed for this question: {command}"))
        if re.search(r"\.\.[\\/]", line):
            issues.append(StaticIssue(code="PATH_ESCAPE", message="path traversal detected"))
    return issues


def scan_script_code(submitted_code: str) -> list[StaticIssue]:
    """对脚本题做静态检查。

    先复用 shell 检查规则，
    然后额外检查一些脚本题更容易出现的问题，
    比如明显的无限循环写法。
    """

    issues = scan_shell_code(submitted_code, [])
    lowered = submitted_code.lower()
    if "while true" in lowered or "while :" in lowered:
        issues.append(StaticIssue(code="POSSIBLE_INFINITE_LOOP", message="possible infinite loop detected"))
    return issues
