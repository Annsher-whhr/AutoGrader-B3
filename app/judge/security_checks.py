import re
import shlex

from app.schemas import StaticIssue


DANGEROUS_TOKENS = {"rm", "sudo", "shutdown", "reboot", "mkfs", "curl", "wget", "nc", "netcat", "powershell", "cmd.exe"}
FORBIDDEN_CHARS = ["&&", "||", ">", ">>", "<", "`", "${", "|&"]


def _contains_unquoted_semicolon(text: str) -> bool:
    in_single = False
    in_double = False
    escaped = False
    for char in text:
        if escaped:
            escaped = False
            continue
        if char == "\\" and not in_single:
            escaped = True
            continue
        if char == "'" and not in_double:
            in_single = not in_single
            continue
        if char == '"' and not in_single:
            in_double = not in_double
            continue
        if char == ";" and not in_single and not in_double:
            return True
    return False


def _contains_command_substitution(text: str) -> bool:
    in_single = False
    in_double = False
    escaped = False
    for index, char in enumerate(text):
        if escaped:
            escaped = False
            continue
        if char == "\\" and not in_single:
            escaped = True
            continue
        if char == "'" and not in_double:
            in_single = not in_single
            continue
        if char == '"' and not in_single:
            in_double = not in_double
            continue
        if char == "$" and not in_single and index + 1 < len(text) and text[index + 1] == "(":
            if index + 2 < len(text) and text[index + 2] == "(":
                continue
            return True
    return False


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
    if _contains_unquoted_semicolon(submitted_code):
        issues.append(StaticIssue(code="FORBIDDEN_SHELL_SYNTAX", message="dangerous shell syntax detected: ;"))
    if _contains_command_substitution(submitted_code):
        issues.append(StaticIssue(code="FORBIDDEN_SHELL_SYNTAX", message="dangerous shell syntax detected: $("))
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

    issues = [issue for issue in scan_shell_code(submitted_code, []) if issue.code != "TOO_MANY_LINES"]
    lowered = submitted_code.lower()
    expected = "4,6,8,9,10,12,14,15,16,18,20,21,22,24,25,26,27,28,30,32,33,34,35,36,38,39,40,42,44,45,46,48,49,50,51,52,54,55,56,57,58,60,62,63,64,65,66,68,69,70,72,74,75,76,77,78,80,81,82,84,85,86,87,88,90,91,92,93,94,95,96,98,99,100"
    if "while true" in lowered or "while :" in lowered:
        issues.append(StaticIssue(code="POSSIBLE_INFINITE_LOOP", message="possible infinite loop detected"))
    if expected in submitted_code and ("for " not in lowered and "while " not in lowered):
        issues.append(StaticIssue(code="HARDCODED_EXPECTED_OUTPUT", message="hardcoded expected output detected"))
    return issues
