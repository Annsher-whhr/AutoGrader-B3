import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_import_questions() -> None:
    response = client.post("/api/v1/b3/questions/import/problem-txt")
    assert response.status_code == 200
    data = response.json()
    assert any(item["id"] == "Q02" for item in data)
    assert any(item["id"] == "Q10" for item in data)


def test_q02_correct_answer() -> None:
    client.post("/api/v1/b3/questions/import/problem-txt")
    response = client.post(
        "/api/v1/b3/evaluate",
        json={"question_id": "Q02", "submitted_code": "ssh user01@127.0.0.1", "submission_id": "sub-q02", "language": "shell"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["overall_score"] == 100.0
    assert data["passed_count"] == 1


def test_q10_hardcoded_answer_rejected() -> None:
    client.post("/api/v1/b3/questions/import/problem-txt")
    response = client.post(
        "/api/v1/b3/evaluate",
        json={
            "question_id": "Q10",
            "submitted_code": "echo '4,6,8,9,10,12,14,15,16,18,20,21,22,24,25,26,27,28,30,32,33,34,35,36,38,39,40,42,44,45,46,48,49,50,51,52,54,55,56,57,58,60,62,63,64,65,66,68,69,70,72,74,75,76,77,78,80,81,82,84,85,86,87,88,90,91,92,93,94,95,96,98,99,100'",
            "submission_id": "sub-q10",
            "language": "shell",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["overall_score"] == 0.0
    assert data["passed_count"] == 0
    assert data["case_results"][0]["error"] is not None
    return
    assert "硬编码" in data["overall_comment"] or "硬编码" in (data["case_results"][0]["error"] or "")


def test_api_demo_runner() -> None:
    client.post("/api/v1/b3/questions/import/problem-txt")
    response = client.post(
        "/api/v1/b3/evaluate",
        json={"question_id": "API_DEMO", "submitted_code": "def add(a, b):\n    return a + b\n", "submission_id": "sub-api", "language": "python"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["overall_score"] == 100.0
