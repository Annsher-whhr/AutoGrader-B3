from typing import Any

from pydantic import BaseModel, Field


class TestCaseRead(BaseModel):
    """返回给前端或调用方的“测试用例”数据结构。"""

    id: int
    case_no: int
    description: str
    input_data: str | None = None
    expected_output: str | None = None
    score_weight: float
    input_files_json: dict[str, str] | None = None
    expected_files_json: dict[str, str] | None = None
    call_args_json: Any = None
    is_hidden: bool

    model_config = {"from_attributes": True}


class QuestionRead(BaseModel):
    """题目列表和题目更新接口会返回的基础题目信息。"""

    id: str
    title: str
    description: str
    question_type: str
    difficulty: str
    language: str
    time_limit_ms: int
    memory_limit_mb: int
    allowed_commands: list[str]
    metadata_json: dict
    status: str

    model_config = {"from_attributes": True}


class QuestionDetail(QuestionRead):
    """题目详情结构。

    它继承了 `QuestionRead` 的字段，
    并额外带上了该题的全部测试用例。
    """

    test_cases: list[TestCaseRead]


class QuestionUpdate(BaseModel):
    """题目更新接口的请求体。

    这里全部使用可选字段，
    表示调用方只需要传自己想修改的部分即可。
    """

    title: str | None = None
    description: str | None = None
    difficulty: str | None = None
    time_limit_ms: int | None = None
    memory_limit_mb: int | None = None
    allowed_commands: list[str] | None = None
    metadata_json: dict | None = None
    status: str | None = None


class EvaluateRequest(BaseModel):
    """提交答案时使用的请求体。"""

    question_id: str
    submitted_code: str = Field(min_length=1)
    submission_id: str = "manual"
    language: str = "shell"


class StaticIssue(BaseModel):
    """静态检查阶段发现的问题。

    例如：
    - 使用了危险命令
    - 出现了不允许的 shell 语法
    - 脚本疑似死循环
    """

    code: str
    message: str


class EvaluationCaseResultRead(BaseModel):
    """单个测试用例的评测结果结构。"""

    case_id: str
    description: str
    passed: bool
    score: float
    actual_output: str | None = None
    expected_output: str | None = None
    error: str | None = None
    execution_time_ms: float


class EvaluationResponse(BaseModel):
    """评测接口最终返回的完整响应结构。"""

    question_id: str
    submission_id: str
    overall_score: float
    passed_count: int
    total_count: int
    overall_comment: str
    static_issues: list[StaticIssue]
    case_results: list[EvaluationCaseResultRead]
