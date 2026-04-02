import re
import shlex
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory


@dataclass
class CaseExecution:
    """shell 判题函数统一返回的结果结构。

    不同题目的检查逻辑虽然不一样，
    但最后都会整理成同一种结构，方便上层评测服务统一处理。
    """

    passed: bool
    actual_output: str | None
    expected_output: str | None
    error: str | None


def _split_lines(code: str) -> list[str]:
    """把提交内容按行拆开，并去掉空行。

    这样后面的判题逻辑只需要关心真正有内容的命令行。
    """

    return [line.strip() for line in code.splitlines() if line.strip()]


def _tokens(line: str) -> list[str]:
    """把一行 shell 命令拆成参数列表。

    这里使用 `shlex.split()`，
    它比普通的字符串 `split()` 更适合处理带引号的 shell 命令。
    """

    return shlex.split(line)


def _normalize_space(text: str) -> str:
    """把连续空白压缩成一个空格。

    这样可以避免用户只是通过换行、多个空格等格式变化，
    来绕过“是否硬编码结果”的简单检查。
    """

    return re.sub(r"\s+", " ", text.strip())


def check_q02(code: str) -> CaseExecution:
    """检查 Q02 的答案是否是符合要求的 SSH 登录命令。"""

    lines = _split_lines(code)
    if len(lines) != 1:
        return CaseExecution(False, str(lines), "1 line", "答案应只包含 1 行 ssh 命令。")
    line = lines[0]
    patterns = [r"^ssh\s+user01@127\.0\.0\.1$", r"^ssh\s+-l\s+user01\s+127\.0\.0\.1$"]
    passed = any(re.fullmatch(pattern, line) for pattern in patterns)
    return CaseExecution(passed, line, "ssh user01@127.0.0.1", None if passed else "ssh 目标或用户不正确。")


def check_q03(code: str) -> CaseExecution:
    """检查 Q03。

    这道题要求提交固定顺序的 5 条系统命令，
    所以这里会逐行拆开，然后按顺序逐条校验。
    """

    lines = _split_lines(code)
    expected = [
        lambda t: t[:2] == ["who", "-b"] or t == ["who", "--boot"],
        lambda t: t[:2] == ["uname", "-r"],
        lambda t: t == ["date", "+%Y|%m|%d_%H:%M"],
        lambda t: t == ["cal", "10", "1949"] or t == ["cal", "1949", "10"],
        lambda t: t == ["cat", "week5_5.txt"],
    ]
    if len(lines) != 5:
        return CaseExecution(False, str(lines), "5 lines", "答案必须为 5 行命令。")
    for idx, line in enumerate(lines):
        if not expected[idx](_tokens(line)):
            return CaseExecution(False, line, f"line {idx + 1}", f"第 {idx + 1} 行命令不符合要求。")
    return CaseExecution(True, "\n".join(lines), "valid command sequence", None)


def check_q04(code: str) -> CaseExecution:
    """检查 Q04 的目录切换与文件拼接命令序列。"""

    lines = _split_lines(code)
    validators = [
        lambda t: t == ["cd", "week5_6"],
        lambda t: t == ["pwd"],
        lambda t: t == ["cd", ".."],
        lambda t: t == ["pwd"],
        lambda t: t == ["cat", "week5_10_1.txt", "week5_10_2.txt", "week5_10_3.txt"],
    ]
    if len(lines) != 5:
        return CaseExecution(False, str(lines), "5 lines", "答案必须为 5 行命令。")
    for idx, line in enumerate(lines):
        if not validators[idx](_tokens(line)):
            return CaseExecution(False, line, f"line {idx + 1}", f"第 {idx + 1} 行命令不符合要求。")
    return CaseExecution(True, "\n".join(lines), "valid command sequence", None)


def check_q05(code: str) -> CaseExecution:
    """检查 Q05 的文件查看、复制、重命名命令。"""

    lines = _split_lines(code)
    validators = [
        lambda t: t == ["head", "-5", "week5_11.txt"],
        lambda t: t == ["tail", "-5", "week5_12.txt"],
        lambda t: t in (["ls", "-ali"], ["ls", "-ail"], ["ls", "-lai"], ["ls", "-lia"]),
        lambda t: t == ["cp", "week5_14.log", "week5_14_dest"],
        lambda t: t == ["mv", "week5_15.log", "week5_15.txt"],
    ]
    if len(lines) != 5:
        return CaseExecution(False, str(lines), "5 lines", "答案必须为 5 行命令。")
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        # 这里临时构造出题目里约定的文件环境。
        # 虽然当前校验主要还是看命令结构，但把场景数据写清楚，
        # 后续如果想升级成更真实的执行型校验，会更容易扩展。
        (root / "week5_11.txt").write_text("1\n2\n3\n4\n5\n6\n", encoding="utf-8")
        (root / "week5_12.txt").write_text("a\nb\nc\nd\ne\nf\n", encoding="utf-8")
        (root / "week5_14.log").write_text("copy me\n", encoding="utf-8")
        (root / "week5_15.log").write_text("rename me\n", encoding="utf-8")
        (root / ".hidden").write_text("x\n", encoding="utf-8")
        (root / "week5_14_dest").mkdir()
        for idx, line in enumerate(lines):
            if not validators[idx](_tokens(line)):
                return CaseExecution(False, line, f"line {idx + 1}", f"第 {idx + 1} 行命令不符合要求。")
    return CaseExecution(True, "\n".join(lines), "valid file ops", None)


def check_q06(code: str) -> CaseExecution:
    """检查 Q06。

    这道题允许两种 chmod 写法：
    - 符号模式，例如 `u+x,g-w,o=r`
    - 数字模式，例如 `754`
    """

    lines = _split_lines(code)
    if len(lines) != 2:
        return CaseExecution(False, str(lines), "2 lines", "答案必须为 2 行命令。")
    vi_line, chmod_line = lines
    if "week6_1.txt" not in vi_line or "line22222222" not in vi_line or "+x" not in vi_line:
        return CaseExecution(False, vi_line, "vi command", "vi 命令未体现插入、删除并保存退出。")
    chmod_tokens = _tokens(chmod_line)
    accepted = chmod_tokens == ["chmod", "u+x,g-w,o=r", "week6_2.dat"] or chmod_tokens == ["chmod", "754", "week6_2.dat"]
    if not accepted:
        return CaseExecution(False, chmod_line, "chmod u+x,g-w,o=r week6_2.dat", "chmod 权限设置不正确。")
    return CaseExecution(True, "\n".join(lines), "valid vi + chmod", None)


def check_q07(code: str) -> CaseExecution:
    """检查 Q07 的 grep / sort 管道命令结构。

    这里不是逐字符完全匹配，
    而是检查关键命令和关键参数有没有出现。
    这样可以允许用户在不影响正确性的前提下有一些写法差异。
    """

    lines = _split_lines(code)
    validations = [
        lambda line: "grep" in line and "-i" in line and "-c" in line and "linux" in line.lower() and "week7.txt" in line,
        lambda line: "grep" in line and "-c" in line and "^$" in line and "week7.txt" in line,
        lambda line: line.count("grep") >= 2 and "-n" in line,
        lambda line: "grep" in line and "-E" in line and "sort" in line and "-nr" in line,
        lambda line: "grep" in line and "-E" in line and "sort" in line and "-r" in line,
    ]
    if len(lines) != 5:
        return CaseExecution(False, str(lines), "5 lines", "答案必须为 5 行命令。")
    for idx, line in enumerate(lines):
        if not validations[idx](line):
            return CaseExecution(False, line, f"line {idx + 1}", f"第 {idx + 1} 行命令结构不符合要求。")
    return CaseExecution(True, "\n".join(lines), "valid grep/sort commands", None)


def check_q08(code: str) -> CaseExecution:
    """检查 Q08 的两条 sed 命令。"""

    lines = _split_lines(code)
    if len(lines) != 2:
        return CaseExecution(False, str(lines), "2 lines", "答案必须为 2 行命令。")
    ok1 = "sed" in lines[0] and "argument" in lines[0].lower() and ("-n" in lines[0] or "p" in lines[0])
    ok2 = "sed" in lines[1] and "argument" in lines[1].lower() and ":" in lines[1]
    if not ok1:
        return CaseExecution(False, lines[0], "sed line numbers", "第 1 行 sed 命令不符合要求。")
    if not ok2:
        return CaseExecution(False, lines[1], "sed with line:text", "第 2 行 sed 命令不符合要求。")
    return CaseExecution(True, "\n".join(lines), "valid sed commands", None)


def check_q09(code: str) -> CaseExecution:
    """检查 Q09 的 awk 统计与筛选命令。"""

    lines = _split_lines(code)
    if len(lines) != 2:
        return CaseExecution(False, str(lines), "2 lines", "答案必须为 2 行命令。")
    ok1 = "awk" in lines[0] and "sales" in lines[0] and ("sum" in lines[0].lower() or "avg" in lines[0].lower())
    ok2 = "awk" in lines[1] and "varun" in lines[1]
    if not ok1:
        return CaseExecution(False, lines[0], "awk average sales", "第 1 行 awk 命令不符合要求。")
    if not ok2:
        return CaseExecution(False, lines[1], "awk print varun", "第 2 行 awk 命令不符合要求。")
    return CaseExecution(True, "\n".join(lines), "valid awk commands", None)


def check_q10(code: str) -> CaseExecution:
    """检查 Q10 的脚本题答案。

    这道题的重点不是“把正确结果写出来”，
    而是“通过脚本逻辑算出来”。

    所以这里会重点检查：
    - 有没有直接把完整答案硬编码进去
    - 有没有循环结构
    - 有没有条件判断
    - 有没有输出语句
    """

    expected = "4,6,8,9,10,12,14,15,16,18,20,21,22,24,25,26,27,28,30,32,33,34,35,36,38,39,40,42,44,45,46,48,49,50,51,52,54,55,56,57,58,60,62,63,64,65,66,68,69,70,72,74,75,76,77,78,80,81,82,84,85,86,87,88,90,91,92,93,94,95,96,98,99,100"
    compact = _normalize_space(code)
    if expected in compact and ("for " not in code and "while " not in code):
        return CaseExecution(False, code, expected, "检测到直接硬编码结果，未体现脚本计算过程。")
    if "for " not in code and "while " not in code:
        return CaseExecution(False, code, "loop-based script", "脚本缺少循环结构。")
    if "if " not in code and "[[" not in code and "test " not in code:
        return CaseExecution(False, code, "conditional logic", "脚本缺少判定逻辑。")
    if "echo" not in code and "printf" not in code:
        return CaseExecution(False, code, "echo/printf", "脚本未输出结果。")
    return CaseExecution(True, None, expected + "\n", None)


CHECKERS = {
    # 评测服务会根据题目 ID，从这里找到对应的判题函数。
    # 这样新增题目时，只要补一个 `check_xx` 函数并注册到这里即可。
    "Q02": check_q02,
    "Q03": check_q03,
    "Q04": check_q04,
    "Q05": check_q05,
    "Q06": check_q06,
    "Q07": check_q07,
    "Q08": check_q08,
    "Q09": check_q09,
    "Q10": check_q10,
}
