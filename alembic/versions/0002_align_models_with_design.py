"""Align ORM schema with system design document.

Revision ID: 0002_align_models_with_design
Revises: 0001_initial_schema
Create Date: 2026-05-13 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_align_models_with_design"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("test_cases", sa.Column("case_id", sa.String(length=64), nullable=True))
    if op.get_bind().dialect.name == "mysql":
        op.execute("UPDATE test_cases SET case_id = CONCAT('case_', LPAD(case_no, 2, '0')) WHERE case_id IS NULL")
    else:
        op.execute("UPDATE test_cases SET case_id = 'case_' || substr('00' || case_no, -2, 2) WHERE case_id IS NULL")
    with op.batch_alter_table("test_cases") as batch_op:
        batch_op.alter_column("case_id", existing_type=sa.String(length=64), nullable=False)

    op.drop_table("evaluation_case_results")
    op.drop_index(op.f("ix_evaluation_records_submission_id"), table_name="evaluation_records")
    op.drop_table("evaluation_records")

    op.create_table(
        "users",
        sa.Column("user_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("username", sa.String(length=20), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=32), nullable=True),
        sa.Column("real_name", sa.String(length=100), nullable=False),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("avatar_url", sa.String(length=512), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("username"),
    )
    op.create_table(
        "students",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("student_id", sa.String(length=64), nullable=False),
        sa.Column("first_password_changed", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("student_id"),
    )
    op.create_table(
        "teachers",
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("teacher_id", sa.String(length=64), nullable=False),
        sa.Column("department", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("teacher_id"),
    )
    op.create_table(
        "courses",
        sa.Column("course_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("course_code", sa.String(length=64), nullable=False),
        sa.Column("course_name", sa.String(length=255), nullable=False),
        sa.Column("teacher_id", sa.Integer(), nullable=False),
        sa.Column("semester", sa.String(length=64), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("course_id"),
    )
    op.create_table(
        "classes",
        sa.Column("class_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("course_id", sa.Integer(), nullable=False),
        sa.Column("class_name", sa.String(length=255), nullable=False),
        sa.Column("class_code", sa.String(length=64), nullable=False),
        sa.Column("teacher_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["course_id"], ["courses.course_id"]),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("class_id"),
    )
    op.create_table(
        "class_students",
        sa.Column("class_id", sa.Integer(), nullable=False),
        sa.Column("student_user_id", sa.Integer(), nullable=False),
        sa.Column("joined_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["class_id"], ["classes.class_id"]),
        sa.ForeignKeyConstraint(["student_user_id"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("class_id", "student_user_id"),
    )
    op.create_table(
        "assignments",
        sa.Column("assignment_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("class_id", sa.Integer(), nullable=False),
        sa.Column("teacher_id", sa.Integer(), nullable=False),
        sa.Column("due_date", sa.DateTime(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False),
        sa.Column("allow_resubmit", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("question_id", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["class_id"], ["classes.class_id"]),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"]),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("assignment_id"),
    )
    op.create_table(
        "submissions",
        sa.Column("submission_id", sa.String(length=64), nullable=False),
        sa.Column("student_user_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.String(length=32), nullable=False),
        sa.Column("assignment_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=True),
        sa.Column("passed_count", sa.Integer(), nullable=True),
        sa.Column("total_count", sa.Integer(), nullable=True),
        sa.Column("overall_comment", sa.Text(), nullable=True),
        sa.Column("static_issues", sa.JSON(), nullable=True),
        sa.Column("case_results", sa.JSON(), nullable=True),
        sa.Column("teacher_score_override", sa.Float(), nullable=True),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["assignment_id"], ["assignments.assignment_id"]),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"]),
        sa.ForeignKeyConstraint(["student_user_id"], ["users.user_id"]),
        sa.PrimaryKeyConstraint("submission_id"),
    )


def downgrade() -> None:
    op.drop_table("submissions")
    op.drop_table("assignments")
    op.drop_table("class_students")
    op.drop_table("classes")
    op.drop_table("courses")
    op.drop_table("teachers")
    op.drop_table("students")
    op.drop_table("users")

    op.create_table(
        "evaluation_records",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("submission_id", sa.String(length=64), nullable=False),
        sa.Column("question_id", sa.String(length=32), nullable=False),
        sa.Column("submitted_code", sa.Text(), nullable=False),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("overall_score", sa.Float(), nullable=False),
        sa.Column("passed_count", sa.Integer(), nullable=False),
        sa.Column("total_count", sa.Integer(), nullable=False),
        sa.Column("overall_comment", sa.Text(), nullable=False),
        sa.Column("static_issues", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_evaluation_records_submission_id"), "evaluation_records", ["submission_id"], unique=False)
    op.create_table(
        "evaluation_case_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("evaluation_id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.String(length=64), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("passed", sa.Boolean(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("actual_output", sa.Text(), nullable=True),
        sa.Column("expected_output", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("execution_time_ms", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["evaluation_id"], ["evaluation_records.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    with op.batch_alter_table("test_cases") as batch_op:
        batch_op.drop_column("case_id")
