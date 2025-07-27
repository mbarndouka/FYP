"""Add user tables for auth

Revision ID: 002_add_user_tables
Revises: 001_initial_migration
Create Date: 2025-07-22 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '002_add_user_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    
    # Drop existing enum if it exists (this will cascade drop any tables using it)
    try:
        result = conn.execute(sa.text("""
            SELECT 1 FROM pg_type WHERE typname = 'userrole'
        """)).fetchone()
        
        if result:
            conn.execute(sa.text("DROP TYPE userrole CASCADE"))
    except Exception:
        pass
    
    # Create the enum type
    user_role_enum = postgresql.ENUM(
        'admin', 'field_team', 'geoscientist', 'reservoir_engineer', 
        'environmental_officer', 'manager', 'new_employee',
        name='userrole'
    )
    user_role_enum.create(conn)

    # Create users table
    op.create_table('users',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('role', postgresql.ENUM(
            'admin', 'field_team', 'geoscientist', 'reservoir_engineer', 
            'environmental_officer', 'manager', 'new_employee',
            name='userrole', create_type=False
        ), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('profile_image_url', sa.String(length=500), nullable=True),
        sa.Column('department', sa.String(length=100), nullable=True),
        sa.Column('phone_number', sa.String(length=20), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_login', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # Create user_sessions table
    op.create_table('user_sessions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('is_revoked', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_user_sessions_id'), 'user_sessions', ['id'], unique=False)
    op.create_index(op.f('ix_user_sessions_user_id'), 'user_sessions', ['user_id'], unique=False)


def downgrade() -> None:
    # Drop indexes and tables
    op.drop_index(op.f('ix_user_sessions_user_id'), table_name='user_sessions')
    op.drop_index(op.f('ix_user_sessions_id'), table_name='user_sessions')
    op.drop_table('user_sessions')
    
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    
    # Drop enum
    conn = op.get_bind()
    try:
        conn.execute(sa.text("DROP TYPE userrole CASCADE"))
    except Exception:
        # Enum might already be dropped
        pass
