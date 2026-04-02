from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Question, TestCase
from app.problem_parser import parse_problem_sections
from app.seed_data import API_DEMO_QUESTION, build_seeded_questions


def list_questions(db: Session) -> list[Question]:
    """查询全部题目，并按题号排序返回。

    这样前端每次看到的列表顺序都会比较稳定。
    """

    stmt = select(Question).order_by(Question.id)
    return list(db.scalars(stmt))


def get_question(db: Session, question_id: str) -> Question | None:
    """按题目 ID 查询单道题，同时把它的测试用例一起加载出来。

    `selectinload(Question.test_cases)` 的作用是提前把关联的测试用例查出来，
    避免后面访问 `question.test_cases` 时再额外触发数据库查询。
    """

    stmt = select(Question).where(Question.id == question_id).options(selectinload(Question.test_cases))
    return db.scalar(stmt)


def import_seed_questions(db: Session) -> list[Question]:
    """导入 B3 题库。

    当前导入流程分两部分：
    1. 从 `problem.txt` 解析题目正文描述
    2. 用代码里的蓝图补齐判题所需的结构化配置

    这样既能真正依赖原始题面文件，又能保留当前版本所需的测试数据和判题规则。
    """

    imported: list[Question] = []
    existing_ids = set(db.scalars(select(Question.id)).all())
    problem_txt_path = Path(__file__).resolve().parents[2] / "problem.txt"
    problem_sections = parse_problem_sections(problem_txt_path)
    parsed_questions = build_seeded_questions(problem_sections)
    for payload in parsed_questions + [API_DEMO_QUESTION]:
        if payload["id"] in existing_ids:
            existing = db.get(Question, payload["id"])
            if existing is not None:
                imported.append(existing)
            continue
        # 这里把 `seed_data.py` 里用字典描述的题目，
        # 转成真正的 ORM 对象，后面才能写入数据库。
        question = Question(
            id=payload["id"],
            title=payload["title"],
            description=payload["description"],
            question_type=payload["question_type"],
            difficulty=payload["difficulty"],
            language="python" if payload["question_type"] == "api" else "shell",
            allowed_commands=payload["allowed_commands"],
            metadata_json=payload["metadata_json"],
        )
        for case in payload["cases"]:
            question.test_cases.append(
                TestCase(
                    case_no=case["case_no"],
                    description=case["description"],
                    input_data=case.get("input_data"),
                    expected_output=case.get("expected_output"),
                    score_weight=case.get("score_weight", 1.0),
                    input_files_json=case.get("input_files_json"),
                    expected_files_json=case.get("expected_files_json"),
                    call_args_json=case.get("call_args_json"),
                    is_hidden=case.get("is_hidden", False),
                )
            )
        db.add(question)
        imported.append(question)
        existing_ids.add(payload["id"])
    db.commit()
    return imported
