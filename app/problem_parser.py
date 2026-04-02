import re
from pathlib import Path


QUESTION_HEADER_RE = re.compile(r"(?m)^第\s*(\d+)\s*题")


def _normalize_problem_text(text: str) -> str:
    """清理 problem.txt 中的控制字符和多余空行。"""

    text = text.replace("\r", "\n").replace("\ufeff", "")
    text = text.replace("\u2028", "\n").replace("\u2029", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def parse_problem_sections(problem_txt_path: str | Path) -> dict[int, str]:
    """按“第N题”标题把 problem.txt 切成题目编号到题面正文的映射。"""

    text = Path(problem_txt_path).read_text(encoding="utf-8")
    normalized = _normalize_problem_text(text)
    matches = list(QUESTION_HEADER_RE.finditer(normalized))
    sections: dict[int, str] = {}
    for index, match in enumerate(matches):
        question_no = int(match.group(1))
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
        body = normalized[start:end].strip()
        sections[question_no] = body
    return sections
