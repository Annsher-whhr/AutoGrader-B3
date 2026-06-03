from datetime import UTC, datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, Enum, Float, ForeignKey, Integer, JSON, PrimaryKeyConstraint, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

BIGINT = BigInteger().with_variant(Integer, "sqlite")
_EMPTY_BLUEPRINT = {"allowed_commands": [], "metadata_json": {}, "cases": []}
_RUNTIME_BLUEPRINTS: dict[str, dict[str, Any]] = {}
_RUNTIME_CASES: dict[tuple[str, int], dict[str, Any]] = {}


def normalize_question_type(value: str | None) -> str:
    normalized = (value or "command").strip().lower()
    return {
        "shell": "command",
        "bash": "command",
        "cli": "command",
        "command_line": "command",
        "file_io": "file",
        "python": "api",
        "interface": "api",
    }.get(normalized, normalized)


def utc_now() -> datetime:
    """返回当前 UTC 时间，使用带时区的时间对象。"""

    return datetime.now(UTC)


def register_question_blueprint(question_id: str, blueprint: dict[str, Any]) -> None:
    """注册运行时创建或更新的判题专用字段。"""

    cases = list(blueprint.get("cases", []))
    stored = dict(blueprint)
    stored["id"] = question_id
    stored["cases"] = cases
    _RUNTIME_BLUEPRINTS[question_id] = stored
    for index, case in enumerate(cases, start=1):
        case_payload = dict(case)
        case_no = int(case_payload.get("case_no") or index)
        case_payload["case_no"] = case_no
        _RUNTIME_CASES[(question_id, case_no)] = case_payload


def _question_blueprint(question_id: str | None) -> dict[str, Any]:
    if not question_id:
        return dict(_EMPTY_BLUEPRINT)
    from app.seed_data import API_DEMO_QUESTION, EXTERNAL_QUESTION_BLUEPRINTS, QUESTION_BLUEPRINTS

    seeded = None
    for blueprint in [*EXTERNAL_QUESTION_BLUEPRINTS, *QUESTION_BLUEPRINTS, API_DEMO_QUESTION]:
        if blueprint["id"] == question_id:
            seeded = blueprint
            break
    runtime = _RUNTIME_BLUEPRINTS.get(question_id)
    if runtime is None:
        return seeded or dict(_EMPTY_BLUEPRINT)
    merged = dict(seeded or _EMPTY_BLUEPRINT)
    merged.update(runtime)
    if "cases" not in runtime and seeded is not None:
        merged["cases"] = seeded.get("cases", [])
    return merged


def _case_blueprint(question_id: str | None, case_no: int) -> dict[str, Any]:
    seeded_case = {}
    for case in _question_blueprint(question_id).get("cases", []):
        if case.get("case_no") == case_no:
            seeded_case = case
            break
    if question_id is None:
        return seeded_case
    runtime_case = _RUNTIME_CASES.get((question_id, case_no))
    if runtime_case is None:
        return seeded_case
    return {**seeded_case, **runtime_case}


class Question(Base):
    """题目表，字段名对齐远程联调库。"""

    __tablename__ = "questions"

    question_id: Mapped[str] = mapped_column(String(50), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    type: Mapped[str] = mapped_column(Enum("COMMAND_LINE", "FILE_IO", "INTERFACE", name="question_type"), nullable=False)
    difficulty: Mapped[str] = mapped_column(Enum("EASY", "MEDIUM", "HARD", name="question_difficulty"), nullable=False)
    language: Mapped[str] = mapped_column(String(20), nullable=False)
    time_limit: Mapped[int | None] = mapped_column(Integer)
    memory_limit: Mapped[int | None] = mapped_column(Integer)
    starter_code: Mapped[str | None] = mapped_column(Text)
    solution_code: Mapped[str | None] = mapped_column(Text)
    judge_config_json: Mapped[dict[str, Any] | None] = mapped_column("judge_config", JSON)
    is_active: Mapped[bool | None] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"))

    test_cases: Mapped[list["TestCase"]] = relationship(back_populates="question", cascade="all, delete-orphan", order_by="TestCase.test_case_id")
    creator: Mapped["User | None"] = relationship(back_populates="created_questions", foreign_keys=[created_by])

    @property
    def id(self) -> str:
        return self.question_id

    @id.setter
    def id(self, value: str) -> None:
        self.question_id = value

    @property
    def question_type(self) -> str:
        if self.question_id == "Q10":
            return "script"
        return {"INTERFACE": "api", "FILE_IO": "file", "COMMAND_LINE": "command"}.get(self.type, self.type.lower())

    @question_type.setter
    def question_type(self, value: str) -> None:
        normalized = normalize_question_type(value)
        self.type = {"api": "INTERFACE", "file": "FILE_IO", "script": "COMMAND_LINE", "command": "COMMAND_LINE"}.get(normalized, normalized)

    @property
    def time_limit_ms(self) -> int:
        return self.time_limit or 2000

    @time_limit_ms.setter
    def time_limit_ms(self, value: int) -> None:
        self.time_limit = value

    @property
    def memory_limit_mb(self) -> int:
        return self.memory_limit or 64

    @memory_limit_mb.setter
    def memory_limit_mb(self, value: int) -> None:
        self.memory_limit = value

    @property
    def allowed_commands(self) -> list[str]:
        if self.judge_config_json and "allowed_commands" in self.judge_config_json:
            return list(self.judge_config_json.get("allowed_commands") or [])
        return list(_question_blueprint(self.question_id).get("allowed_commands", []))

    @allowed_commands.setter
    def allowed_commands(self, value: list[str]) -> None:
        self._allowed_commands_hint = value
        config = dict(self.judge_config_json or {})
        config["allowed_commands"] = list(value or [])
        self.judge_config_json = config

    @property
    def metadata_json(self) -> dict[str, Any]:
        if self.judge_config_json and "metadata_json" in self.judge_config_json:
            return dict(self.judge_config_json.get("metadata_json") or {})
        return dict(_question_blueprint(self.question_id).get("metadata_json", {}))

    @metadata_json.setter
    def metadata_json(self, value: dict[str, Any]) -> None:
        self._metadata_json_hint = value
        config = dict(self.judge_config_json or {})
        config["metadata_json"] = dict(value or {})
        self.judge_config_json = config

    @property
    def status(self) -> str:
        return "ACTIVE" if self.is_active is not False else "INACTIVE"

    @status.setter
    def status(self, value: str) -> None:
        self.is_active = value == "ACTIVE"


class TestCase(Base):
    """测试用例表，字段名对齐远程联调库。"""

    __tablename__ = "test_cases"

    test_case_id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.question_id", ondelete="CASCADE"), nullable=False, index=True)
    case_id_value: Mapped[str | None] = mapped_column("case_id", String(50))
    case_no_value: Mapped[int | None] = mapped_column("case_no", Integer)
    description_text: Mapped[str | None] = mapped_column("description", Text)
    input: Mapped[str | None] = mapped_column(Text)
    expected_output: Mapped[str] = mapped_column(Text, nullable=False)
    input_files_json_value: Mapped[dict[str, str] | None] = mapped_column("input_files_json", JSON)
    expected_files_json_value: Mapped[dict[str, str] | None] = mapped_column("expected_files_json", JSON)
    call_args_json_value: Mapped[Any] = mapped_column("call_args_json", JSON)
    is_public: Mapped[bool | None] = mapped_column(Boolean, default=True)
    score_weight: Mapped[float] = mapped_column(Float, default=1.0)

    question: Mapped["Question"] = relationship(back_populates="test_cases")

    @property
    def id(self) -> int:
        return self.test_case_id

    @id.setter
    def id(self, value: int) -> None:
        self.test_case_id = value

    @property
    def case_no(self) -> int:
        if self.case_no_value is not None:
            return self.case_no_value
        if hasattr(self, "_case_no_hint"):
            return self._case_no_hint
        if self.question is not None:
            ordered = sorted(self.question.test_cases, key=lambda item: item.test_case_id or 0)
            for index, item in enumerate(ordered, start=1):
                if item is self:
                    return index
        return int(self.test_case_id or 1)

    @case_no.setter
    def case_no(self, value: int) -> None:
        self._case_no_hint = value
        self.case_no_value = value

    @property
    def case_id(self) -> str:
        if self.case_id_value:
            return self.case_id_value
        return f"case_{self.case_no:02d}"

    @case_id.setter
    def case_id(self, value: str) -> None:
        self._case_id_hint = value
        self.case_id_value = value

    @property
    def description(self) -> str:
        if self.description_text:
            return self.description_text
        return _case_blueprint(self.question_id, self.case_no).get("description", self.case_id)

    @description.setter
    def description(self, value: str) -> None:
        self._description_hint = value
        self.description_text = value

    @property
    def input_data(self) -> str | None:
        return self.input or _case_blueprint(self.question_id, self.case_no).get("input_data")

    @input_data.setter
    def input_data(self, value: str | None) -> None:
        self.input = value

    @property
    def input_files_json(self) -> dict[str, str] | None:
        if self.input_files_json_value is not None:
            return self.input_files_json_value
        return _case_blueprint(self.question_id, self.case_no).get("input_files_json")

    @input_files_json.setter
    def input_files_json(self, value: dict[str, str] | None) -> None:
        self._input_files_json_hint = value
        self.input_files_json_value = value

    @property
    def expected_files_json(self) -> dict[str, str] | None:
        if self.expected_files_json_value is not None:
            return self.expected_files_json_value
        return _case_blueprint(self.question_id, self.case_no).get("expected_files_json")

    @expected_files_json.setter
    def expected_files_json(self, value: dict[str, str] | None) -> None:
        self._expected_files_json_hint = value
        self.expected_files_json_value = value

    @property
    def call_args_json(self) -> Any:
        if self.call_args_json_value is not None:
            return self.call_args_json_value
        return _case_blueprint(self.question_id, self.case_no).get("call_args_json")

    @call_args_json.setter
    def call_args_json(self, value: Any) -> None:
        self._call_args_json_hint = value
        self.call_args_json_value = value

    @property
    def is_hidden(self) -> bool:
        return self.is_public is False

    @is_hidden.setter
    def is_hidden(self, value: bool) -> None:
        self.is_public = not value


class User(Base):
    """系统用户表。

    保存学生、教师、管理员的公共账号信息。
    """

    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20))
    real_name: Mapped[str] = mapped_column(String(50), nullable=False)
    role: Mapped[str] = mapped_column(Enum("student", "teacher", "admin", name="user_role"), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool | None] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)

    student_profile: Mapped["Student | None"] = relationship(back_populates="user", cascade="all, delete-orphan")
    teacher_profile: Mapped["Teacher | None"] = relationship(back_populates="user", cascade="all, delete-orphan")
    courses: Mapped[list["Course"]] = relationship(back_populates="teacher", foreign_keys="Course.teacher_id")
    classes: Mapped[list["Class"]] = relationship(back_populates="teacher", foreign_keys="Class.teacher_id")
    class_memberships: Mapped[list["ClassStudent"]] = relationship(back_populates="student", foreign_keys="ClassStudent.student_user_id")
    assignments: Mapped[list["Assignment"]] = relationship(back_populates="teacher", foreign_keys="Assignment.teacher_id")
    submissions: Mapped[list["Submission"]] = relationship(back_populates="student", foreign_keys="Submission.student_user_id")
    created_questions: Mapped[list["Question"]] = relationship(back_populates="creator", foreign_keys="Question.created_by")
    announcements: Mapped[list["Announcement"]] = relationship(back_populates="creator", foreign_keys="Announcement.created_by")
    system_logs: Mapped[list["SystemLog"]] = relationship(back_populates="user")


class Student(Base):
    """学生扩展表。"""

    __tablename__ = "students"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    student_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    first_password_changed: Mapped[bool | None] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(back_populates="student_profile")


class Teacher(Base):
    """教师扩展表。"""

    __tablename__ = "teachers"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), primary_key=True)
    teacher_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    department: Mapped[str | None] = mapped_column(String(100))

    user: Mapped["User"] = relationship(back_populates="teacher_profile")


class Course(Base):
    """课程表。"""

    __tablename__ = "courses"

    course_id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    course_code: Mapped[str] = mapped_column(String(50), nullable=False)
    course_name: Mapped[str] = mapped_column(String(100), nullable=False)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    semester: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    teacher: Mapped["User"] = relationship(back_populates="courses", foreign_keys=[teacher_id])
    classes: Mapped[list["Class"]] = relationship(back_populates="course", cascade="all, delete-orphan")
    announcements: Mapped[list["Announcement"]] = relationship(back_populates="course", cascade="all, delete-orphan")


class Class(Base):
    """班级表。"""

    __tablename__ = "classes"

    class_id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.course_id", ondelete="CASCADE"), nullable=False)
    class_name: Mapped[str] = mapped_column(String(100), nullable=False)
    class_code: Mapped[str] = mapped_column(String(20), nullable=False)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    course: Mapped["Course"] = relationship(back_populates="classes")
    teacher: Mapped["User"] = relationship(back_populates="classes", foreign_keys=[teacher_id])
    students: Mapped[list["ClassStudent"]] = relationship(back_populates="class_", cascade="all, delete-orphan")
    assignments: Mapped[list["Assignment"]] = relationship(back_populates="class_", cascade="all, delete-orphan")


class ClassStudent(Base):
    """学生-班级关联表。"""

    __tablename__ = "class_students"
    __table_args__ = (PrimaryKeyConstraint("class_id", "student_user_id"),)

    class_id: Mapped[int] = mapped_column(ForeignKey("classes.class_id", ondelete="CASCADE"), nullable=False)
    student_user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    class_: Mapped["Class"] = relationship(back_populates="students")
    student: Mapped["User"] = relationship(back_populates="class_memberships", foreign_keys=[student_user_id])


class Assignment(Base):
    """作业表。

    一个作业只绑定一道 B-3 题库题目。
    """

    __tablename__ = "assignments"

    assignment_id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.class_id", ondelete="CASCADE"), nullable=False)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    due_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_published: Mapped[bool | None] = mapped_column(Boolean, default=False)
    allow_resubmit: Mapped[bool | None] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    question_id: Mapped[str] = mapped_column(String(50), nullable=False)

    class_: Mapped["Class"] = relationship(back_populates="assignments")
    teacher: Mapped["User"] = relationship(back_populates="assignments", foreign_keys=[teacher_id])
    submissions: Mapped[list["Submission"]] = relationship(back_populates="assignment", cascade="all, delete-orphan")


class Submission(Base):
    """提交记录表。

    B-2/B-4 先创建提交，B-3 评测完成后按 submission_id 回填结果。
    """

    __tablename__ = "submissions"

    submission_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    student_user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), nullable=False)
    question_id: Mapped[str] = mapped_column(String(50), nullable=False)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.assignment_id", ondelete="CASCADE"), nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str | None] = mapped_column(String(20), default="python")
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    status: Mapped[str] = mapped_column(Enum("PENDING", "RUNNING", "COMPLETED", "ERROR", name="submission_status"), nullable=False)
    overall_score: Mapped[float | None] = mapped_column(Float)
    passed_count: Mapped[int | None] = mapped_column(Integer)
    total_count: Mapped[int | None] = mapped_column(Integer)
    overall_comment: Mapped[str | None] = mapped_column(Text)
    static_issues: Mapped[list | None] = mapped_column(JSON)
    case_results: Mapped[list | None] = mapped_column(JSON)
    teacher_score_override: Mapped[float | None] = mapped_column(Float)
    override_reason: Mapped[str | None] = mapped_column(Text)

    student: Mapped["User"] = relationship(back_populates="submissions", foreign_keys=[student_user_id])
    assignment: Mapped["Assignment"] = relationship(back_populates="submissions")


class Announcement(Base):
    """课程公告表。"""

    __tablename__ = "announcements"

    announcement_id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    course_id: Mapped[int | None] = mapped_column(ForeignKey("courses.course_id", ondelete="CASCADE"))
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    course: Mapped["Course | None"] = relationship(back_populates="announcements")
    creator: Mapped["User | None"] = relationship(back_populates="announcements", foreign_keys=[created_by])


class SystemConfig(Base):
    """系统配置表。"""

    __tablename__ = "system_config"

    config_key: Mapped[str] = mapped_column(String(100), primary_key=True)
    config_value: Mapped[str] = mapped_column(Text, nullable=False)
    config_type: Mapped[str | None] = mapped_column(String(20))
    description: Mapped[str | None] = mapped_column(String(500))


class SystemLog(Base):
    """系统日志表。"""

    __tablename__ = "system_logs"

    log_id: Mapped[int] = mapped_column(BIGINT, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.user_id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(50))
    target_id: Mapped[str | None] = mapped_column(String(100))
    details: Mapped[dict | None] = mapped_column(JSON)
    ip_address: Mapped[str | None] = mapped_column(String(50))
    level: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    user: Mapped["User | None"] = relationship(back_populates="system_logs")
