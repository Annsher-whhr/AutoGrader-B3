from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Question, TestCase
from app.seed_data import API_DEMO_QUESTION, SEEDED_QUESTIONS


def list_questions(db: Session) -> list[Question]:
    stmt = select(Question).order_by(Question.id)
    return list(db.scalars(stmt))


def get_question(db: Session, question_id: str) -> Question | None:
    stmt = select(Question).where(Question.id == question_id).options(selectinload(Question.test_cases))
    return db.scalar(stmt)


def import_seed_questions(db: Session) -> list[Question]:
    imported: list[Question] = []
    existing_ids = set(db.scalars(select(Question.id)).all())
    for payload in SEEDED_QUESTIONS + [API_DEMO_QUESTION]:
        if payload["id"] in existing_ids:
            existing = db.get(Question, payload["id"])
            if existing is not None:
                imported.append(existing)
            continue
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
