import os

# 在导入应用之前，先强制把数据库切换成内存数据库。
# 这样测试不会污染本地真实数据库，测试进程结束后数据也会自动消失。
os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["DEBUG"] = "true"
os.environ["SANDBOX_BACKEND"] = "local"

import pytest
from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app


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
    assert cases[0]["case_no"] == 1


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


def test_missing_question_endpoints_return_404() -> None:
    """验证查询或评测不存在的题目时会返回 404。"""

    detail_response = client.get("/api/v1/b3/questions/NO_SUCH_QUESTION")
    assert detail_response.status_code == 404

    cases_response = client.get("/api/v1/b3/questions/NO_SUCH_QUESTION/cases")
    assert cases_response.status_code == 404

    evaluate_response = client.post(
        "/api/v1/b3/evaluate",
        json={"question_id": "NO_SUCH_QUESTION", "submitted_code": "echo ok", "submission_id": "missing", "language": "shell"},
    )
    assert evaluate_response.status_code == 404


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


@pytest.mark.parametrize("question_id", ["Q02", "Q03", "Q04", "Q05", "Q06", "Q07", "Q08", "Q09", "Q10"])
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
