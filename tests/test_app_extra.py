import os
from datetime import UTC, datetime, timedelta

# 在导入应用之前，先强制把数据库切换成内存数据库。
# 这样测试不会污染本地真实数据库，测试进程结束后数据也会自动消失。
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["DEBUG"] = "true"
os.environ["SANDBOX_BACKEND"] = "local"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import Assignment, Class, ClassStudent, Course, Question, Submission, User


Base.metadata.create_all(bind=engine)
client = TestClient(app)


def test_health_endpoint() -> None:
    """验证健康检查接口能正常返回服务状态。"""

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_question_list_detail_and_cases() -> None:
    """验证题目列表、详情和测试用例接口都能正常读取数据。"""

    client.post("/api/v1/b3/questions/import/problem-txt")

    list_response = client.get("/api/v1/b3/questions")
    assert list_response.status_code == 200
    questions = list_response.json()
    assert any(item["id"] == "Q02" for item in questions)

    detail_response = client.get("/api/v1/b3/questions/Q02")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["id"] == "Q02"
    assert len(detail["test_cases"]) >= 1

    cases_response = client.get("/api/v1/b3/questions/Q02/cases")
    assert cases_response.status_code == 200
    cases = cases_response.json()
    assert len(cases) >= 1
    assert cases[0]["case_id"] == "case_01"
    assert cases[0]["case_no"] == 1


def test_question_rules_endpoint_for_python_api_question() -> None:
    """验证 B3 提供 B2 静态检查需要的 Python 规则。"""

    client.post("/api/v1/b3/questions/import/problem-txt")
    response = client.get("/api/v1/b3/rules/API_DEMO")
    assert response.status_code == 200
    data = response.json()
    assert data["question_id"] == "API_DEMO"
    assert data["question_type"] == "api"
    assert data["language"] == "python"
    assert "os" in data["forbidden_modules"]
    assert "subprocess" in data["forbidden_modules"]
    assert "eval" in data["forbidden_functions"]
    assert "exec" in data["forbidden_functions"]


def test_question_rules_endpoint_for_shell_question() -> None:
    """验证 rules 接口会返回 shell 题的命令白名单。"""

    client.post("/api/v1/b3/questions/import/problem-txt")
    response = client.get("/api/v1/b3/rules/Q01")
    assert response.status_code == 200
    data = response.json()
    assert data["question_id"] == "Q01"
    assert data["question_type"] == "command"
    assert data["language"] == "shell"
    assert data["allowed_commands"] == ["echo", "mail"]


def test_unprefixed_api_v1_routes_remain_compatible() -> None:
    """验证联调方可以不带 /b3 前缀访问主要接口。"""

    client.post("/api/v1/b3/questions/import/problem-txt")
    response = client.get("/api/v1/questions/Q02")
    assert response.status_code == 200
    assert response.json()["id"] == "Q02"

    rules_response = client.get("/api/v1/rules/API_DEMO")
    assert rules_response.status_code == 200
    assert rules_response.json()["question_id"] == "API_DEMO"


def test_design_tables_and_class_students_primary_key_exist() -> None:
    """验证文档要求的核心业务表已经进入 ORM 元数据。"""

    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    assert {
        "users",
        "students",
        "teachers",
        "courses",
        "classes",
        "class_students",
        "assignments",
        "submissions",
    }.issubset(table_names)
    assert set(inspector.get_pk_constraint("class_students")["constrained_columns"]) == {"class_id", "student_user_id"}


def test_submission_result_updates_existing_submission() -> None:
    """验证 B-3 只回填已存在的 submissions 记录。"""

    client.post("/api/v1/b3/questions/import/problem-txt")
    submission_id = "existing-submission-update"

    with SessionLocal() as db:
        student = User(
            username="student_existing_submission",
            password_hash="hash",
            email="student_existing_submission@example.com",
            real_name="测试学生",
            role="student",
        )
        teacher = User(
            username="teacher_existing_submission",
            password_hash="hash",
            email="teacher_existing_submission@example.com",
            real_name="测试教师",
            role="teacher",
        )
        db.add_all([student, teacher])
        db.commit()
        db.refresh(student)
        db.refresh(teacher)

        course = Course(course_code="CS102-T1", course_name="Python 程序设计", teacher_id=teacher.user_id, semester="2025-2026-2")
        db.add(course)
        db.commit()
        db.refresh(course)

        class_ = Class(course_id=course.course_id, class_name="软件工程2班", class_code="01", teacher_id=teacher.user_id)
        db.add(class_)
        db.commit()
        db.refresh(class_)

        db.add(ClassStudent(class_id=class_.class_id, student_user_id=student.user_id))
        assignment = Assignment(
            title="SSH 登录题作业",
            class_id=class_.class_id,
            teacher_id=teacher.user_id,
            due_date=datetime.now(UTC) + timedelta(days=1),
            question_id="Q02",
        )
        db.add(assignment)
        db.commit()
        db.refresh(assignment)

        db.add(
            Submission(
                submission_id=submission_id,
                student_user_id=student.user_id,
                question_id="Q02",
                assignment_id=assignment.assignment_id,
                code="",
                language="shell",
                status="PENDING",
            )
        )
        db.commit()

    response = client.post(
        "/api/v1/b3/evaluate",
        json={"question_id": "Q02", "submitted_code": "ssh user01@127.0.0.1\nexit", "submission_id": submission_id, "language": "shell"},
    )
    assert response.status_code == 200

    with SessionLocal() as db:
        submission = db.get(Submission, submission_id)
        assert submission is not None
        assert submission.status == "COMPLETED"
        assert submission.overall_score == 100.0
        assert submission.passed_count == 1
        assert submission.total_count == 1
        assert submission.code == "ssh user01@127.0.0.1\nexit"
        assert submission.case_results is not None
        assert submission.case_results[0]["case_id"] == "case_01"


def test_evaluate_without_submission_does_not_create_partial_submission() -> None:
    """验证找不到 submission_id 时，B-3 不创建缺少学生和作业信息的记录。"""

    client.post("/api/v1/b3/questions/import/problem-txt")
    submission_id = "missing-submission-no-create"
    response = client.post(
        "/api/v1/b3/evaluate",
        json={"question_id": "Q02", "submitted_code": "ssh user01@127.0.0.1\nexit", "submission_id": submission_id, "language": "shell"},
    )

    assert response.status_code == 200
    with SessionLocal() as db:
        assert db.get(Submission, submission_id) is None


def test_import_uses_problem_txt_description() -> None:
    """验证导题接口会把 problem.txt 中的原始题面写入题目描述。"""

    client.post("/api/v1/b3/questions/import/problem-txt")
    response = client.get("/api/v1/b3/questions/Q02")
    assert response.status_code == 200
    detail = response.json()
    assert "使用ssh命令登录到127.0.0.1主机" in detail["description"]
    assert "附件里只能包含linux命令" in detail["description"]


def test_question_update() -> None:
    """验证题目更新接口只会更新传入的字段。"""

    client.post("/api/v1/b3/questions/import/problem-txt")
    response = client.put(
        "/api/v1/b3/questions/Q02",
        json={"title": "新的题目标题", "difficulty": "HARD"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "新的题目标题"
    assert data["difficulty"] == "HARD"


def test_create_question_keeps_runtime_judge_fields() -> None:
    """验证 JSON 创建题目后，判题字段和用例描述能被 B3 读取。"""

    question_id = "Q_RUNTIME_CREATE"
    response = client.post(
        "/api/v1/b3/questions",
        json={
            "id": question_id,
            "title": "动态 echo 题",
            "description": "输出 hello",
            "question_type": "command",
            "difficulty": "EASY",
            "allowed_commands": ["echo"],
            "metadata_json": {"source": "api"},
            "test_cases": [
                {
                    "case_no": 1,
                    "description": "输出 hello",
                    "expected_output": "hello\n",
                    "score_weight": 1.0,
                }
            ],
        },
    )
    assert response.status_code == 201
    created = response.json()
    assert created["allowed_commands"] == ["echo"]
    assert created["metadata_json"] == {"source": "api"}
    assert created["test_cases"][0]["description"] == "输出 hello"

    detail_response = client.get(f"/api/v1/b3/questions/{question_id}")
    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["allowed_commands"] == ["echo"]
    assert detail["metadata_json"] == {"source": "api"}
    assert detail["test_cases"][0]["description"] == "输出 hello"

    evaluate_response = client.post(
        "/api/v1/b3/evaluate",
        json={"question_id": question_id, "submitted_code": "echo hello", "submission_id": "runtime-create", "language": "shell"},
    )
    assert evaluate_response.status_code == 200
    result = evaluate_response.json()
    assert result["overall_score"] == 100.0
    assert result["case_results"][0]["description"] == "输出 hello"


def test_missing_question_endpoints_return_404() -> None:
    """验证查询或评测不存在的题目时会返回 404。"""

    detail_response = client.get("/api/v1/b3/questions/NO_SUCH_QUESTION")
    assert detail_response.status_code == 404

    cases_response = client.get("/api/v1/b3/questions/NO_SUCH_QUESTION/cases")
    assert cases_response.status_code == 404

    rules_response = client.get("/api/v1/b3/rules/NO_SUCH_QUESTION")
    assert rules_response.status_code == 404

    evaluate_response = client.post(
        "/api/v1/b3/evaluate",
        json={"question_id": "NO_SUCH_QUESTION", "submitted_code": "echo ok", "submission_id": "missing", "language": "shell"},
    )
    assert evaluate_response.status_code == 404


def test_unknown_question_blueprint_has_safe_defaults() -> None:
    """验证外部库题目即使没有 B3 蓝图，也能安全序列化。"""

    question_id = "Q_EXTERNAL_DEFAULTS"
    with SessionLocal() as db:
        if db.get(Question, question_id) is None:
            db.add(
                Question(
                    id=question_id,
                    title="外部题目",
                    description="来自其他模块的题目",
                    question_type="command",
                    difficulty="EASY",
                    language="shell",
                )
            )
            db.commit()

    response = client.get(f"/api/v1/b3/questions/{question_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["allowed_commands"] == []
    assert data["metadata_json"] == {}


def test_evaluate_question_without_cases_returns_clear_error() -> None:
    """验证题目无测试用例时不再返回 0/0 的模糊评测结果。"""

    question_id = "Q_EMPTY_CASES"
    with SessionLocal() as db:
        if db.get(Question, question_id) is None:
            db.add(
                Question(
                    id=question_id,
                    title="无测试点题目",
                    description="用于验证空测试点行为",
                    question_type="command",
                    difficulty="EASY",
                    language="shell",
                )
            )
            db.commit()

    response = client.post(
        "/api/v1/b3/evaluate",
        json={"question_id": question_id, "submitted_code": "echo ok", "submission_id": "empty-cases", "language": "shell"},
    )
    assert response.status_code == 422
    assert "no test cases" in response.json()["detail"]


def test_q02_disallowed_command_rejected_by_static_scan() -> None:
    """验证命令题会拦截不在白名单中的命令。"""

    client.post("/api/v1/b3/questions/import/problem-txt")
    response = client.post(
        "/api/v1/b3/evaluate",
        json={"question_id": "Q02", "submitted_code": "ls", "submission_id": "sub-q02-bad", "language": "shell"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["overall_score"] == 0.0
    assert data["static_issues"]
    assert any(issue["code"] == "COMMAND_NOT_ALLOWED" for issue in data["static_issues"])


def test_q02_forbidden_shell_syntax_rejected() -> None:
    """验证静态检查会拦截危险的 shell 拼接语法。"""

    client.post("/api/v1/b3/questions/import/problem-txt")
    response = client.post(
        "/api/v1/b3/evaluate",
        json={"question_id": "Q02", "submitted_code": "ssh user01@127.0.0.1 && whoami", "submission_id": "sub-q02-and", "language": "shell"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["overall_score"] == 0.0
    assert any(issue["code"] == "FORBIDDEN_SHELL_SYNTAX" for issue in data["static_issues"])


def test_q10_path_escape_rejected_by_static_scan() -> None:
    """验证脚本题会拦截明显的路径越界访问。"""

    client.post("/api/v1/b3/questions/import/problem-txt")
    response = client.post(
        "/api/v1/b3/evaluate",
        json={"question_id": "Q10", "submitted_code": "cat ../secret.txt", "submission_id": "sub-q10-path", "language": "shell"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["overall_score"] == 0.0
    assert any(issue["code"] == "PATH_ESCAPE" for issue in data["static_issues"])


def test_q10_infinite_loop_pattern_rejected() -> None:
    """验证脚本题会拦截明显的无限循环写法。"""

    client.post("/api/v1/b3/questions/import/problem-txt")
    response = client.post(
        "/api/v1/b3/evaluate",
        json={"question_id": "Q10", "submitted_code": "while true\ndo\n  echo x\ndone", "submission_id": "sub-q10-loop", "language": "shell"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["overall_score"] == 0.0
    assert any(issue["code"] == "POSSIBLE_INFINITE_LOOP" for issue in data["static_issues"])


def test_api_demo_forbidden_import_rejected() -> None:
    """验证 API 题会拦截危险模块导入。"""

    client.post("/api/v1/b3/questions/import/problem-txt")
    response = client.post(
        "/api/v1/b3/evaluate",
        json={"question_id": "API_DEMO", "submitted_code": "import os\n\ndef add(a, b):\n    return a + b\n", "submission_id": "sub-api-import", "language": "python"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["overall_score"] == 0.0
    assert data["passed_count"] == 0
    assert data["case_results"][0]["error"] is not None


def test_api_demo_timeout_isolated_from_main_process() -> None:
    """验证 API 题超时后会被安全终止，而不是卡住主服务进程。"""

    client.post("/api/v1/b3/questions/import/problem-txt")
    update_response = client.put(
        "/api/v1/b3/questions/API_DEMO",
        json={"time_limit_ms": 100},
    )
    assert update_response.status_code == 200

    response = client.post(
        "/api/v1/b3/evaluate",
        json={"question_id": "API_DEMO", "submitted_code": "def add(a, b):\n    while True:\n        pass\n", "submission_id": "sub-api-timeout", "language": "python"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["overall_score"] == 0.0
    assert data["passed_count"] == 0
    assert "超时" in (data["case_results"][0]["error"] or "")


@pytest.mark.parametrize("question_id", ["Q01", "Q02", "Q03", "Q04", "Q05", "Q06", "Q07", "Q08", "Q09", "Q10"])
def test_reference_answers_cover_dynamic_runner(question_id: str) -> None:
    """验证 shell/file/script 题已经改成可执行式评测。"""

    client.post("/api/v1/b3/questions/import/problem-txt")
    response = client.post(f"/api/v1/b3/evaluate/answer/{question_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["question_id"] == question_id
    assert data["overall_score"] == 100.0
    assert data["passed_count"] == data["total_count"]
    assert data["case_results"][0]["execution_time_ms"] >= 0.0


def test_q05_dynamic_judge_checks_file_state() -> None:
    """验证文件题不只看命令文本，还会检查执行后的文件结果。"""

    client.post("/api/v1/b3/questions/import/problem-txt")
    response = client.post(
        "/api/v1/b3/evaluate",
        json={
            "question_id": "Q05",
            "submitted_code": "head -5 week5_11.txt\ntail -5 week5_12.txt\nls -ali\ncp week5_14.log week5_14_dest\nmv week5_15.log wrong.txt",
            "submission_id": "sub-q05-wrong-state",
            "language": "shell",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["overall_score"] == 0.0
    assert "week5_15.txt" in (data["case_results"][0]["error"] or "")


def test_q08_readonly_input_file_cannot_be_modified() -> None:
    """验证纯读取题的输入文件会被设置为只读，不能在答题时修改内容。"""

    client.post("/api/v1/b3/questions/import/problem-txt")
    response = client.post(
        "/api/v1/b3/evaluate",
        json={
            "question_id": "Q08",
            "submitted_code": "sed -i '1s/first/HACKED/' week8.txt\nsed -n '/[Aa]rgument/=' week8.txt",
            "submission_id": "sub-q08-write-readonly",
            "language": "shell",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["overall_score"] == 0.0
    error_text = data["case_results"][0]["error"] or ""
    assert "readonly path modified" in error_text or "命令退出码" in error_text or "Permission denied" in error_text


def test_q06_writable_files_remain_modifiable() -> None:
    """验证允许修改的文件不会被新的只读策略误伤。"""

    client.post("/api/v1/b3/questions/import/problem-txt")
    response = client.post(
        "/api/v1/b3/evaluate",
        json={
            "question_id": "Q06",
            "submitted_code": "vi +$'e week6_1.txt' +$':2' +$'i\\n[line22222222]' +$':5d' +x\nchmod u+x,g-w,o=r week6_2.dat",
            "submission_id": "sub-q06-writable-check",
            "language": "shell",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["overall_score"] == 100.0


def test_reference_answer_endpoint() -> None:
    """验证参考答案接口能走通完整评测流程。"""

    client.post("/api/v1/b3/questions/import/problem-txt")
    response = client.post("/api/v1/b3/evaluate/answer/Q02")
    assert response.status_code == 200
    data = response.json()
    assert data["question_id"] == "Q02"
    assert data["overall_score"] == 100.0
