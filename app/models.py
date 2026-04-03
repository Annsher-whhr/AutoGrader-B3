from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utc_now() -> datetime:
    """返回当前 UTC 时间，使用带时区的时间对象。"""

    return datetime.now(UTC)


class Question(Base):
    """题目表。

    这个模型保存一题的核心信息：
    - 题目编号、标题、描述
    - 题目类型，例如命令题、脚本题、API 题
    - 判题所需的限制，例如允许的命令、时间限制、内存限制
    """

    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[str] = mapped_column(String(32), nullable=False)
    difficulty: Mapped[str] = mapped_column(String(16), default="MEDIUM")
    language: Mapped[str] = mapped_column(String(16), default="shell")
    time_limit_ms: Mapped[int] = mapped_column(Integer, default=2000)
    memory_limit_mb: Mapped[int] = mapped_column(Integer, default=64)
    allowed_commands: Mapped[list[str]] = mapped_column(JSON, default=list)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(16), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now, onupdate=utc_now)

    test_cases: Mapped[list["TestCase"]] = relationship(back_populates="question", cascade="all, delete-orphan")
    evaluation_records: Mapped[list["EvaluationRecord"]] = relationship(back_populates="question")


class TestCase(Base):
    """测试用例表。

    一道题可以对应多个测试用例。
    对于 API 题，通常会真的逐个测试用例执行；
    对于当前的 shell 题，很多时候是把第一条用例当成展示和记录用的信息。
    """

    __tablename__ = "test_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id"), nullable=False, index=True)
    case_no: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    input_data: Mapped[str | None] = mapped_column(Text)
    expected_output: Mapped[str | None] = mapped_column(Text)
    score_weight: Mapped[float] = mapped_column(Float, default=1.0)
    input_files_json: Mapped[dict | None] = mapped_column(JSON)
    expected_files_json: Mapped[dict | None] = mapped_column(JSON)
    call_args_json: Mapped[dict | list | None] = mapped_column(JSON)
    is_hidden: Mapped[bool] = mapped_column(Boolean, default=False)

    question: Mapped["Question"] = relationship(back_populates="test_cases")


class EvaluationRecord(Base):
    """提交记录表。

    每当用户提交一次答案，就会生成一条评测记录。
    这里保存的是“整次提交”的总体结果，比如总分、通过数、总体评语等。
    """

    __tablename__ = "evaluation_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    submission_id: Mapped[str] = mapped_column(String(64), index=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id"), nullable=False)
    submitted_code: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(16), nullable=False)
    overall_score: Mapped[float] = mapped_column(Float, default=0.0)
    passed_count: Mapped[int] = mapped_column(Integer, default=0)
    total_count: Mapped[int] = mapped_column(Integer, default=0)
    overall_comment: Mapped[str] = mapped_column(Text, default="")
    static_issues: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(16), default="COMPLETED")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    question: Mapped["Question"] = relationship(back_populates="evaluation_records")
    case_results: Mapped[list["EvaluationCaseResult"]] = relationship(back_populates="record", cascade="all, delete-orphan")


class EvaluationCaseResult(Base):
    """单个测试用例的评测结果。

    这张表和 `EvaluationRecord` 是一对多关系：
    一次提交可以包含多个测试用例结果。
    """

    __tablename__ = "evaluation_case_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    evaluation_id: Mapped[int] = mapped_column(ForeignKey("evaluation_records.id"), nullable=False)
    case_id: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    score: Mapped[float] = mapped_column(Float, default=0.0)
    actual_output: Mapped[str | None] = mapped_column(Text)
    expected_output: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    execution_time_ms: Mapped[float] = mapped_column(Float, default=0.0)

    record: Mapped["EvaluationRecord"] = relationship(back_populates="case_results")
