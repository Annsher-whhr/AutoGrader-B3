from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.judge.dynamic_runner import python_judge_mode
from app.judge.api_runner import FORBIDDEN_CALLS, FORBIDDEN_IMPORTS
from app.models import Question, TestCase, normalize_question_type, register_question_blueprint
from app.problem_parser import parse_problem_sections
from app.schemas import QuestionCreate, QuestionRules
from app.seed_data import API_DEMO_QUESTION, EXTERNAL_QUESTION_BLUEPRINTS, build_seeded_questions


def _build_test_case(case: dict) -> TestCase:
    return TestCase(
        case_id=case.get("case_id", f"case_{case['case_no']:02d}"),
        case_no=case["case_no"],
        description=case["description"],
        input_data=case.get("input_data"),
        expected_output=case.get("expected_output") or "",
        score_weight=case.get("score_weight", 1.0),
        input_files_json=case.get("input_files_json"),
        expected_files_json=case.get("expected_files_json"),
        call_args_json=case.get("call_args_json"),
        is_hidden=case.get("is_hidden", False),
    )


def _question_payload_for_runtime(question: Question, cases: list[dict] | None = None) -> dict:
    return {
        "id": question.id,
        "title": question.title,
        "description": question.description,
        "question_type": question.question_type,
        "difficulty": question.difficulty,
        "allowed_commands": getattr(question, "_allowed_commands_hint", question.allowed_commands),
        "metadata_json": getattr(question, "_metadata_json_hint", question.metadata_json),
        "cases": cases or [],
    }


def _case_payloads_for_create(payload: QuestionCreate) -> list[dict]:
    cases: list[dict] = []
    for index, case in enumerate(payload.test_cases, start=1):
        case_payload = case.model_dump()
        case_payload["case_no"] = case_payload.get("case_no") or index
        case_payload["case_id"] = case_payload.get("case_id") or f"case_{case_payload['case_no']:02d}"
        case_payload["description"] = case_payload.get("description") or case_payload["case_id"]
        cases.append(case_payload)
    return cases


def list_questions(db: Session) -> list[Question]:
    """查询全部题目，并按题号排序返回。

    这样前端每次看到的列表顺序都会比较稳定。
    """

    stmt = select(Question).order_by(Question.question_id)
    return list(db.scalars(stmt))


def get_question(db: Session, question_id: str) -> Question | None:
    """按题目 ID 查询单道题，同时把它的测试用例一起加载出来。

    `selectinload(Question.test_cases)` 的作用是提前把关联的测试用例查出来，
    避免后面访问 `question.test_cases` 时再额外触发数据库查询。
    """

    stmt = select(Question).where(Question.question_id == question_id).options(selectinload(Question.test_cases))
    return db.scalar(stmt)


def get_question_rules(question: Question) -> QuestionRules:
    """组装 B2 静态检查需要的题目规则。"""

    metadata = question.metadata_json or {}
    forbidden_modules = metadata.get("forbidden_modules")
    if forbidden_modules is None:
        forbidden_modules = sorted(FORBIDDEN_IMPORTS)
        if question.language == "python" and python_judge_mode(question) == "stdin":
            forbidden_modules = [module for module in forbidden_modules if module != "sys"]
    forbidden_functions = metadata.get("forbidden_functions", sorted(FORBIDDEN_CALLS))
    return QuestionRules(
        question_id=question.id,
        question_type=question.question_type,
        language=question.language,
        allowed_commands=question.allowed_commands,
        forbidden_modules=list(forbidden_modules),
        forbidden_functions=list(forbidden_functions),
        metadata_json=metadata,
    )


def create_question(db: Session, payload: QuestionCreate) -> Question:
    """根据 JSON 请求体创建一道动态 B3 题目。"""

    if db.get(Question, payload.id) is not None:
        raise ValueError(f"Question {payload.id} already exists")

    question_type = normalize_question_type(payload.question_type)
    language = payload.language or ("python" if question_type == "api" else "shell")
    question = Question(
        id=payload.id,
        title=payload.title,
        description=payload.description,
        question_type=question_type,
        difficulty=payload.difficulty,
        language=language,
        time_limit_ms=payload.time_limit_ms,
        memory_limit_mb=payload.memory_limit_mb,
        allowed_commands=payload.allowed_commands,
        metadata_json=payload.metadata_json,
        status=payload.status,
    )
    cases = _case_payloads_for_create(payload)
    for case in cases:
        question.test_cases.append(_build_test_case(case))

    db.add(question)
    db.commit()
    db.refresh(question)
    register_question_blueprint(question.id, _question_payload_for_runtime(question, cases))
    return question


def register_question_runtime_fields(question: Question, fields: dict) -> None:
    """让 API 更新过的判题专用字段继续可读。"""

    runtime_cases = []
    for case in question.test_cases:
        runtime_cases.append(
            {
                "case_no": case.case_no,
                "case_id": case.case_id,
                "description": case.description,
                "input_data": case.input_data,
                "expected_output": case.expected_output,
                "score_weight": case.score_weight,
                "input_files_json": case.input_files_json,
                "expected_files_json": case.expected_files_json,
                "call_args_json": case.call_args_json,
                "is_hidden": case.is_hidden,
            }
        )
    blueprint = _question_payload_for_runtime(question, runtime_cases)
    if "allowed_commands" in fields:
        blueprint["allowed_commands"] = fields["allowed_commands"]
    if "metadata_json" in fields:
        blueprint["metadata_json"] = fields["metadata_json"]
    register_question_blueprint(question.id, blueprint)


def import_seed_questions(db: Session) -> list[Question]:
    """导入 B3 题库。

    当前导入流程分两部分：
    1. 从 `problem.txt` 解析题目正文描述
    2. 用代码里的蓝图补齐判题所需的结构化配置

    这样既能真正依赖原始题面文件，又能保留当前版本所需的测试数据和判题规则。
    """

    imported: list[Question] = []
    existing_ids = set(db.scalars(select(Question.question_id)).all())
    problem_txt_path = Path(__file__).resolve().parents[2] / "problem.txt"
    problem_sections = parse_problem_sections(problem_txt_path)
    parsed_questions = build_seeded_questions(problem_sections)
    for payload in [*EXTERNAL_QUESTION_BLUEPRINTS, *parsed_questions, API_DEMO_QUESTION]:
        if payload["id"] in existing_ids:
            existing = db.get(Question, payload["id"])
            if existing is not None:
                existing_case_numbers = {case.case_no for case in existing.test_cases}
                for case in payload["cases"]:
                    if case["case_no"] not in existing_case_numbers:
                        existing.test_cases.append(_build_test_case(case))
                db.add(existing)
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
            question.test_cases.append(_build_test_case(case))
        db.add(question)
        imported.append(question)
        existing_ids.add(payload["id"])
    db.commit()
    return imported
