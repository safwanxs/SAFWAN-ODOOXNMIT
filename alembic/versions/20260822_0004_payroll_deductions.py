"""Add payroll deduction configuration to salary structures."""

from alembic import op
import sqlalchemy as sa

revision = "20260822_0004"
down_revision = "20260822_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("salary_structures") as batch:
        batch.add_column(sa.Column("pf_employee_percent", sa.Numeric(5, 2), nullable=False, server_default="12"))
        batch.add_column(sa.Column("pf_employer_percent", sa.Numeric(5, 2), nullable=False, server_default="12"))
        batch.add_column(sa.Column("professional_tax", sa.Numeric(12, 2), nullable=False, server_default="0"))


def downgrade() -> None:
    with op.batch_alter_table("salary_structures") as batch:
        batch.drop_column("professional_tax")
        batch.drop_column("pf_employer_percent")
        batch.drop_column("pf_employee_percent")