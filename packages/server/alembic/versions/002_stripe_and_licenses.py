"""Add Stripe fields, licenses table, topup_balance, update subscription tiers.

Revision ID: 002
Revises: 001
Create Date: 2026-04-06
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade():
    # ── Users: add stripe_customer_id and topup_balance ──
    op.add_column("users", sa.Column("stripe_customer_id", sa.String(255), unique=True, nullable=True))
    op.add_column("users", sa.Column("topup_balance", sa.Integer, server_default="0"))

    # ── Licenses table ──
    op.create_table(
        "licenses",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), index=True),
        sa.Column("license_key", sa.String(64), unique=True, nullable=False, index=True),
        sa.Column("device_id", sa.String(255), nullable=True),
        sa.Column("device_name", sa.String(255), nullable=True),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean, server_default="true"),
        sa.Column("stripe_payment_id", sa.String(255), nullable=True),
        sa.Column("version_at_purchase", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── Referrals: add missing columns from the model ──
    op.add_column("referrals", sa.Column("referred_bonus_granted", sa.Boolean, server_default="false"))
    op.add_column("referrals", sa.Column("referrer_bonus_granted", sa.Boolean, server_default="false"))
    op.add_column("referrals", sa.Column("referred_ip", sa.String(45), nullable=True))
    op.add_column("referrals", sa.Column("referred_device_fingerprint", sa.String(255), nullable=True))
    op.add_column("referrals", sa.Column("referred_email_domain", sa.String(255), nullable=True))
    op.add_column("referrals", sa.Column("referral_chain_level", sa.Integer, server_default="1"))
    op.add_column("referrals", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()))


def downgrade():
    op.drop_table("licenses")
    op.drop_column("users", "stripe_customer_id")
    op.drop_column("users", "topup_balance")
    op.drop_column("referrals", "referred_bonus_granted")
    op.drop_column("referrals", "referrer_bonus_granted")
    op.drop_column("referrals", "referred_ip")
    op.drop_column("referrals", "referred_device_fingerprint")
    op.drop_column("referrals", "referred_email_domain")
    op.drop_column("referrals", "referral_chain_level")
    op.drop_column("referrals", "updated_at")
