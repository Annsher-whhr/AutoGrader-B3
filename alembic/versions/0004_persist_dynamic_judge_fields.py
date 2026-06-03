"""Persist dynamic judge fields for frontend-created questions.

Revision ID: 0004_persist_dynamic_judge_fields
Revises: 0003_align_with_remote_schema
Create Date: 2026-06-03 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0004_persist_dynamic_judge_fields"
down_revision = "0003_align_with_remote_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("questions", sa.Column("judge_config", sa.JSON(), nullable=True))
    op.add_column("test_cases", sa.Column("case_id", sa.String(length=50), nullable=True))
    op.add_column("test_cases", sa.Column("case_no", sa.Integer(), nullable=True))
    op.add_column("test_cases", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("test_cases", sa.Column("input_files_json", sa.JSON(), nullable=True))
    op.add_column("test_cases", sa.Column("expected_files_json", sa.JSON(), nullable=True))
    op.add_column("test_cases", sa.Column("call_args_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("test_cases", "call_args_json")
    op.drop_column("test_cases", "expected_files_json")
    op.drop_column("test_cases", "input_files_json")
    op.drop_column("test_cases", "description")
    op.drop_column("test_cases", "case_no")
    op.drop_column("test_cases", "case_id")
    op.drop_column("questions", "judge_config")
