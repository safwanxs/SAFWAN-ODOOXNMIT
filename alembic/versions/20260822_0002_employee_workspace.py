"""Add employee profiles, salary structures, attendance, and leave status."""

from alembic import op
import sqlalchemy as sa

revision = "20260822_0002"
down_revision = "20260822_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "employee_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("about", sa.Text()), sa.Column("interests", sa.Text()), sa.Column("skills", sa.Text()), sa.Column("certifications", sa.Text()),
        sa.Column("date_of_birth", sa.Date()), sa.Column("address", sa.Text()), sa.Column("nationality", sa.String(100)),
        sa.Column("personal_email", sa.String(255)), sa.Column("gender", sa.String(50)), sa.Column("marital_status", sa.String(50)),
        sa.Column("date_of_joining", sa.Date()), sa.Column("bank_account_number", sa.String(100)), sa.Column("bank_name", sa.String(150)),
        sa.Column("ifsc", sa.String(32)), sa.Column("pan", sa.String(32)), sa.Column("uan", sa.String(32)), sa.Column("profile_picture_url", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_employee_profiles_user_id", "employee_profiles", ["user_id"])
    op.create_table(
        "salary_structures",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True),
        sa.Column("wage_type", sa.String(16), nullable=False), sa.Column("total_wage", sa.Numeric(12, 2), nullable=False), sa.Column("components", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_salary_structures_user_id", "salary_structures", ["user_id"])
    op.create_table(
        "attendance",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False), sa.Column("check_in_time", sa.DateTime(timezone=True), nullable=False), sa.Column("check_out_time", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.UniqueConstraint("user_id", "date", name="uq_attendance_user_date"),
    )
    op.create_index("ix_attendance_user_id", "attendance", ["user_id"])
    op.create_table(
        "leave_requests",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False), sa.Column("end_date", sa.Date(), nullable=False), sa.Column("status", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_leave_requests_user_id", "leave_requests", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_leave_requests_user_id", table_name="leave_requests")
    op.drop_table("leave_requests")
    op.drop_index("ix_attendance_user_id", table_name="attendance")
    op.drop_table("attendance")
    op.drop_index("ix_salary_structures_user_id", table_name="salary_structures")
    op.drop_table("salary_structures")
    op.drop_index("ix_employee_profiles_user_id", table_name="employee_profiles")
    op.drop_table("employee_profiles")
