"""Align local schema with the remote autograder database.

Revision ID: 0003_align_with_remote_schema
Revises: 0002_align_models_with_design
Create Date: 2026-05-13 12:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003_align_with_remote_schema"
down_revision = "0002_align_models_with_design"
branch_labels = None
depends_on = None


QUESTION_TYPE = sa.Enum("COMMAND_LINE", "FILE_IO", "INTERFACE", name="question_type")
QUESTION_DIFFICULTY = sa.Enum("EASY", "MEDIUM", "HARD", name="question_difficulty")
USER_ROLE = sa.Enum("student", "teacher", "admin", name="user_role")
SUBMISSION_STATUS = sa.Enum("PENDING", "RUNNING", "COMPLETED", "ERROR", name="submission_status")


def _drop_if_exists(table_name: str) -> None:
    op.execute(f"DROP TABLE IF EXISTS {table_name}")


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        op.execute("SET FOREIGN_KEY_CHECKS=0")
    else:
        op.execute("PRAGMA foreign_keys=OFF")

    op.rename_table("test_cases", "test_cases_legacy_0003")
    op.rename_table("questions", "questions_legacy_0003")
    if bind.dialect.name == "sqlite":
        op.execute("DROP INDEX IF EXISTS ix_test_cases_question_id")
        op.execute("DROP INDEX IF EXISTS ix_test_cases_test_case_id")

    for table_name in [
        "submissions",
        "assignments",
        "class_students",
        "announcements",
        "classes",
        "courses",
        "teachers",
        "students",
        "system_logs",
        "system_config",
        "users",
    ]:
        _drop_if_exists(table_name)

    op.create_table(
        "users",
        sa.Column("user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=20), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=100), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=True),
        sa.Column("real_name", sa.String(length=50), nullable=False),
        sa.Column("role", USER_ROLE, nullable=False),
        sa.Column("avatar_url", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"])
    op.create_index("ix_users_user_id", "users", ["user_id"])
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "courses",
        sa.Column("course_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("course_code", sa.String(length=50), nullable=False),
        sa.Column("course_name", sa.String(length=100), nullable=False),
        sa.Column("teacher_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("semester", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("course_id"),
        sa.UniqueConstraint("course_code", "semester", name="uniq_course"),
    )
    op.create_index("ix_courses_course_id", "courses", ["course_id"])
    op.create_index("ix_courses_teacher_id", "courses", ["teacher_id"])

    op.create_table(
        "questions",
        sa.Column("question_id", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("type", QUESTION_TYPE, nullable=False),
        sa.Column("difficulty", QUESTION_DIFFICULTY, nullable=False),
        sa.Column("language", sa.String(length=20), nullable=False),
        sa.Column("time_limit", sa.Integer(), nullable=True),
        sa.Column("memory_limit", sa.Integer(), nullable=True),
        sa.Column("starter_code", sa.Text(), nullable=True),
        sa.Column("solution_code", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.user_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("question_id"),
    )
    op.create_index("ix_questions_difficulty", "questions", ["difficulty"])
    op.create_index("ix_questions_language", "questions", ["language"])
    op.create_index("ix_questions_type", "questions", ["type"])

    op.execute(
        """
        INSERT INTO questions (
            question_id, title, description, type, difficulty, language,
            time_limit, memory_limit, starter_code, solution_code, is_active, created_at, created_by
        )
        SELECT
            id,
            title,
            description,
            CASE
                WHEN question_type = 'api' THEN 'INTERFACE'
                WHEN question_type = 'file' THEN 'FILE_IO'
                ELSE 'COMMAND_LINE'
            END,
            difficulty,
            language,
            time_limit_ms,
            memory_limit_mb,
            NULL,
            NULL,
            CASE WHEN status = 'ACTIVE' THEN 1 ELSE 0 END,
            created_at,
            NULL
        FROM questions_legacy_0003
        """
    )

    op.create_table(
        "students",
        sa.Column("user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("student_id", sa.String(length=50), nullable=False),
        sa.Column("first_password_changed", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index("ix_students_student_id", "students", ["student_id"], unique=True)

    op.create_table(
        "teachers",
        sa.Column("user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("teacher_id", sa.String(length=50), nullable=False),
        sa.Column("department", sa.String(length=100), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("teacher_id"),
    )

    op.create_table(
        "classes",
        sa.Column("class_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("course_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("class_name", sa.String(length=100), nullable=False),
        sa.Column("class_code", sa.String(length=20), nullable=False),
        sa.Column("teacher_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["course_id"], ["courses.course_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("class_id"),
        sa.UniqueConstraint("course_id", "class_code", name="uniq_class"),
    )
    op.create_index("ix_classes_class_id", "classes", ["class_id"])
    op.create_index("ix_classes_course_id", "classes", ["course_id"])
    op.create_index("ix_classes_teacher_id", "classes", ["teacher_id"])

    op.create_table(
        "announcements",
        sa.Column("announcement_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("course_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_by", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["course_id"], ["courses.course_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["users.user_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("announcement_id"),
    )
    op.create_index("ix_announcements_announcement_id", "announcements", ["announcement_id"])
    op.create_index("ix_announcements_course_id", "announcements", ["course_id"])

    op.create_table(
        "class_students",
        sa.Column("class_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("student_user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("joined_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["class_id"], ["classes.class_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("class_id", "student_user_id"),
    )
    op.create_index("ix_class_students_student_user_id", "class_students", ["student_user_id"])

    op.create_table(
        "assignments",
        sa.Column("assignment_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("class_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("teacher_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("due_date", sa.DateTime(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=True),
        sa.Column("allow_resubmit", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("question_id", sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(["class_id"], ["classes.class_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("assignment_id"),
    )
    op.create_index("ix_assignments_assignment_id", "assignments", ["assignment_id"])
    op.create_index("ix_assignments_class_id", "assignments", ["class_id"])
    op.create_index("ix_assignments_teacher_id", "assignments", ["teacher_id"])

    op.create_table(
        "submissions",
        sa.Column("submission_id", sa.String(length=64), nullable=False),
        sa.Column("student_user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("question_id", sa.String(length=50), nullable=False),
        sa.Column("assignment_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=20), nullable=True),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("status", SUBMISSION_STATUS, nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("passed_count", sa.Integer(), nullable=True),
        sa.Column("total_count", sa.Integer(), nullable=True),
        sa.Column("overall_comment", sa.Text(), nullable=True),
        sa.Column("static_issues", sa.JSON(), nullable=True),
        sa.Column("case_results", sa.JSON(), nullable=True),
        sa.Column("teacher_score_override", sa.Float(), nullable=True),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["assignment_id"], ["assignments.assignment_id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["student_user_id"], ["users.user_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("submission_id"),
    )
    op.create_index("ix_submissions_assignment_id", "submissions", ["assignment_id"])
    op.create_index("ix_submissions_question_id", "submissions", ["question_id"])
    op.create_index("ix_submissions_status", "submissions", ["status"])
    op.create_index("ix_submissions_student_user_id", "submissions", ["student_user_id"])

    op.create_table(
        "system_config",
        sa.Column("config_key", sa.String(length=100), nullable=False),
        sa.Column("config_value", sa.Text(), nullable=False),
        sa.Column("config_type", sa.String(length=20), nullable=True),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint("config_key"),
    )

    op.create_table(
        "system_logs",
        sa.Column("log_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), nullable=True),
        sa.Column("action", sa.String(length=50), nullable=False),
        sa.Column("target_type", sa.String(length=50), nullable=True),
        sa.Column("target_id", sa.String(length=100), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=50), nullable=True),
        sa.Column("level", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("log_id"),
    )
    op.create_index("ix_system_logs_log_id", "system_logs", ["log_id"])

    op.create_table(
        "test_cases",
        sa.Column("test_case_id", sa.BigInteger().with_variant(sa.Integer(), "sqlite"), autoincrement=True, nullable=False),
        sa.Column("question_id", sa.String(length=50), nullable=False),
        sa.Column("input", sa.Text(), nullable=True),
        sa.Column("expected_output", sa.Text(), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=True),
        sa.Column("score_weight", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["question_id"], ["questions.question_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("test_case_id"),
    )
    op.create_index("ix_test_cases_question_id", "test_cases", ["question_id"])
    op.create_index("ix_test_cases_test_case_id", "test_cases", ["test_case_id"])
    op.execute(
        """
        INSERT INTO test_cases (question_id, input, expected_output, is_public, score_weight)
        SELECT question_id, input_data, COALESCE(expected_output, ''), CASE WHEN is_hidden THEN 0 ELSE 1 END, score_weight
        FROM test_cases_legacy_0003
        """
    )

    op.drop_table("test_cases_legacy_0003")
    op.drop_table("questions_legacy_0003")

    if bind.dialect.name == "mysql":
        op.execute("SET FOREIGN_KEY_CHECKS=1")
    else:
        op.execute("PRAGMA foreign_keys=ON")


def downgrade() -> None:
    raise NotImplementedError("Downgrade from remote schema alignment is intentionally not supported.")
