"""Extend leave requests and add leave allocations and public holidays."""

from alembic import op
import sqlalchemy as sa

revision = "20260822_0003"
down_revision = "20260822_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("leave_requests") as batch:
        batch.add_column(sa.Column("leave_type", sa.String(32), nullable=False, server_default="paid_time_off"))
        batch.add_column(sa.Column("days_requested", sa.Integer(), nullable=False, server_default="1"))
        batch.add_column(sa.Column("remarks", sa.Text(), nullable=True))
        batch.add_column(sa.Column("attachment_url", sa.String(500), nullable=True))
        batch.add_column(sa.Column("admin_comment", sa.Text(), nullable=True))
        batch.add_column(sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True))
        batch.add_column(sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
        batch.alter_column("status", existing_type=sa.String(20), server_default="pending")
    op.create_table(
        "leave_allocations",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("leave_type", sa.String(32), nullable=False), sa.Column("days_available", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "leave_type", name="uq_leave_allocation_user_type"),
    )
    op.create_index("ix_leave_allocations_user_id", "leave_allocations", ["user_id"])
    op.create_table(
        "public_holidays",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False), sa.Column("date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_public_holidays_company_id", "public_holidays", ["company_id"])


def downgrade() -> None:
    op.drop_index("ix_public_holidays_company_id", table_name="public_holidays")
    op.drop_table("public_holidays")
    op.drop_index("ix_leave_allocations_user_id", table_name="leave_allocations")
    op.drop_table("leave_allocations")
    with op.batch_alter_table("leave_requests") as batch:
        batch.drop_column("reviewed_at")
        batch.drop_column("reviewed_by")
        batch.drop_column("admin_comment")
        batch.drop_column("attachment_url")
        batch.drop_column("remarks")
        batch.drop_column("days_requested")
        batch.drop_column("leave_type")
