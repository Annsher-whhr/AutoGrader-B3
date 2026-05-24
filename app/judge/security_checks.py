import re
import shlex

from app.schemas import StaticIssue


ALWAYS_DANGEROUS_TOKENS = {"rm", "sudo", "shutdown", "reboot", "mkfs", "powershell", "cmd.exe"}
RESTRICTED_TOKENS = {"curl", "wget", "nc", "netcat", "mail"}
FORBIDDEN_CHARS = ["&&", "||", ">", ">>", "<", "`", "${", "|&"]


def _contains_unquoted_semicolon(text: str) -> bool:
    # 只拦截“命令分隔符”语义的分号；
    # 如果分号出现在引号内，例如 awk / sed 脚本里，就不应该误判。
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
    # 这里要区分 $(...) 和 $((...))：
    # 前者是命令替换，风险更高；后者是算术展开，脚本题里可能合法使用。
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


def _split_unquoted_pipe(text: str) -> list[str]:
    parts: list[str] = []
    start = 0
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
        if char == "|" and not in_single and not in_double:
            parts.append(text[start:index].strip())
            start = index + 1
    parts.append(text[start:].strip())
    return [part for part in parts if part]


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
    allowed = set(allowed_commands)
    for line in lines:
        command_segments = _split_unquoted_pipe(line)
        if not command_segments:
            continue
        if len(command_segments) > 1 and not allowed:
            issues.append(StaticIssue(code="COMMAND_NOT_ALLOWED", message="pipeline commands require an explicit allowed command list"))
            continue
        for segment in command_segments:
            try:
                parts = shlex.split(segment)
            except ValueError:
                issues.append(StaticIssue(code="PARSE_ERROR", message=f"unable to parse command: {segment}"))
                continue
            if not parts:
                continue
            command = parts[0]
            if command in ALWAYS_DANGEROUS_TOKENS or (command in RESTRICTED_TOKENS and command not in allowed):
                issues.append(StaticIssue(code="DANGEROUS_COMMAND", message=f"dangerous command detected: {command}"))
            if allowed and command not in allowed:
                issues.append(StaticIssue(code="COMMAND_NOT_ALLOWED", message=f"command is not allowed for this question: {command}"))
        if re.search(r"\.\.[\\/]", line):
            issues.append(StaticIssue(code="PATH_ESCAPE", message="path traversal detected"))
    return issues


def scan_script_code(submitted_code: str, expected_outputs: list[str] | None = None) -> list[StaticIssue]:
    """对脚本题做静态检查。

    先复用 shell 检查规则，
    然后额外检查一些脚本题更容易出现的问题，
    比如明显的无限循环写法。
    """

    issues = [issue for issue in scan_shell_code(submitted_code, []) if issue.code != "TOO_MANY_LINES"]
    lowered = submitted_code.lower()
    if "while true" in lowered or "while :" in lowered:
        issues.append(StaticIssue(code="POSSIBLE_INFINITE_LOOP", message="possible infinite loop detected"))
    # 对脚本题，直接把任一测试点最终结果硬编码出来不算通过。
    # 期望输出由题目/测试用例传入，避免把某一道题的答案写死在通用扫描器里。
    normalized_submission = submitted_code.replace("\r\n", "\n")
    has_loop_or_condition = any(keyword in lowered for keyword in ("for ", "while ", "until ", "if "))
    for expected in expected_outputs or []:
        normalized_expected = expected.rstrip("\n")
        if normalized_expected and normalized_expected in normalized_submission and not has_loop_or_condition:
            issues.append(StaticIssue(code="HARDCODED_EXPECTED_OUTPUT", message="hardcoded expected output detected"))
            break
    return issues
