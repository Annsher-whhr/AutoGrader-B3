from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, PrimaryKeyConstraint, String, Text
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
    assignments: Mapped[list["Assignment"]] = relationship(back_populates="question")
    submissions: Mapped[list["Submission"]] = relationship(back_populates="question")


class TestCase(Base):
    """测试用例表。

    一道题可以对应多个测试用例。
    对于 API 题，通常会真的逐个测试用例执行；
    对于当前的 shell 题，很多时候是把第一条用例当成展示和记录用的信息。
    """

    __tablename__ = "test_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id"), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(String(64), nullable=False)
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


class User(Base):
    """系统用户表。

    保存学生、教师、管理员的公共账号信息。
    """

    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32))
    real_name: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(512))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)

    student_profile: Mapped["Student | None"] = relationship(back_populates="user", cascade="all, delete-orphan")
    teacher_profile: Mapped["Teacher | None"] = relationship(back_populates="user", cascade="all, delete-orphan")
    courses: Mapped[list["Course"]] = relationship(back_populates="teacher", foreign_keys="Course.teacher_id")
    classes: Mapped[list["Class"]] = relationship(back_populates="teacher", foreign_keys="Class.teacher_id")
    class_memberships: Mapped[list["ClassStudent"]] = relationship(back_populates="student", foreign_keys="ClassStudent.student_user_id")
    assignments: Mapped[list["Assignment"]] = relationship(back_populates="teacher", foreign_keys="Assignment.teacher_id")
    submissions: Mapped[list["Submission"]] = relationship(back_populates="student", foreign_keys="Submission.student_user_id")


class Student(Base):
    """学生扩展表。"""

    __tablename__ = "students"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), primary_key=True)
    student_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    first_password_changed: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(back_populates="student_profile")


class Teacher(Base):
    """教师扩展表。"""

    __tablename__ = "teachers"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), primary_key=True)
    teacher_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    department: Mapped[str | None] = mapped_column(String(255))

    user: Mapped["User"] = relationship(back_populates="teacher_profile")


class Course(Base):
    """课程表。"""

    __tablename__ = "courses"

    course_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_code: Mapped[str] = mapped_column(String(64), nullable=False)
    course_name: Mapped[str] = mapped_column(String(255), nullable=False)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    semester: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    teacher: Mapped["User"] = relationship(back_populates="courses", foreign_keys=[teacher_id])
    classes: Mapped[list["Class"]] = relationship(back_populates="course", cascade="all, delete-orphan")


class Class(Base):
    """班级表。"""

    __tablename__ = "classes"

    class_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.course_id"), nullable=False)
    class_name: Mapped[str] = mapped_column(String(255), nullable=False)
    class_code: Mapped[str] = mapped_column(String(64), nullable=False)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    course: Mapped["Course"] = relationship(back_populates="classes")
    teacher: Mapped["User"] = relationship(back_populates="classes", foreign_keys=[teacher_id])
    students: Mapped[list["ClassStudent"]] = relationship(back_populates="class_", cascade="all, delete-orphan")
    assignments: Mapped[list["Assignment"]] = relationship(back_populates="class_", cascade="all, delete-orphan")


class ClassStudent(Base):
    """学生-班级关联表。"""

    __tablename__ = "class_students"
    __table_args__ = (PrimaryKeyConstraint("class_id", "student_user_id"),)

    class_id: Mapped[int] = mapped_column(ForeignKey("classes.class_id"), nullable=False)
    student_user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)

    class_: Mapped["Class"] = relationship(back_populates="students")
    student: Mapped["User"] = relationship(back_populates="class_memberships", foreign_keys=[student_user_id])


class Assignment(Base):
    """作业表。

    一个作业只绑定一道 B-3 题库题目。
    """

    __tablename__ = "assignments"

    assignment_id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.class_id"), nullable=False)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    due_date: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_resubmit: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    published_at: Mapped[datetime | None] = mapped_column(DateTime)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id"), nullable=False)

    class_: Mapped["Class"] = relationship(back_populates="assignments")
    teacher: Mapped["User"] = relationship(back_populates="assignments", foreign_keys=[teacher_id])
    question: Mapped["Question"] = relationship(back_populates="assignments")
    submissions: Mapped[list["Submission"]] = relationship(back_populates="assignment", cascade="all, delete-orphan")


class Submission(Base):
    """提交记录表。

    B-2/B-4 先创建提交，B-3 评测完成后按 submission_id 回填结果。
    """

    __tablename__ = "submissions"

    submission_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    student_user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), nullable=False)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id"), nullable=False)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignments.assignment_id"), nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(16), default="python")
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=utc_now)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    overall_score: Mapped[float | None] = mapped_column(Float)
    passed_count: Mapped[int | None] = mapped_column(Integer)
    total_count: Mapped[int | None] = mapped_column(Integer)
    overall_comment: Mapped[str | None] = mapped_column(Text)
    static_issues: Mapped[list | None] = mapped_column(JSON)
    case_results: Mapped[list | None] = mapped_column(JSON)
    teacher_score_override: Mapped[float | None] = mapped_column(Float)
    override_reason: Mapped[str | None] = mapped_column(Text)

    student: Mapped["User"] = relationship(back_populates="submissions", foreign_keys=[student_user_id])
    question: Mapped["Question"] = relationship(back_populates="submissions")
    assignment: Mapped["Assignment"] = relationship(back_populates="submissions")
