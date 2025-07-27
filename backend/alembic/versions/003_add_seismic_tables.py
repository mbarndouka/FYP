"""Add seismic tables

Revision ID: 003_add_seismic_tables
Revises: 002_add_user_tables
Create Date: 2025-01-23 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003_add_seismic_tables'
down_revision = '002_add_user_tables'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Create seismic_datasets table
    op.create_table('seismic_datasets',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_format', sa.String(length=50), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('acquisition_date', sa.DateTime(), nullable=True),
        sa.Column('processing_status', sa.String(length=50), nullable=True),
        sa.Column('min_inline', sa.Integer(), nullable=True),
        sa.Column('max_inline', sa.Integer(), nullable=True),
        sa.Column('min_crossline', sa.Integer(), nullable=True),
        sa.Column('max_crossline', sa.Integer(), nullable=True),
        sa.Column('min_time', sa.Float(), nullable=True),
        sa.Column('max_time', sa.Float(), nullable=True),
        sa.Column('sample_rate', sa.Float(), nullable=True),
        sa.Column('trace_count', sa.Integer(), nullable=True),
        sa.Column('inline_increment', sa.Integer(), nullable=True),
        sa.Column('crossline_increment', sa.Integer(), nullable=True),
        sa.Column('crs', sa.String(length=100), nullable=True),
        sa.Column('uploaded_by', sa.Integer(), nullable=True),
        sa.Column('uploaded_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_seismic_datasets_id'), 'seismic_datasets', ['id'], unique=False)
    op.create_index(op.f('ix_seismic_datasets_name'), 'seismic_datasets', ['name'], unique=False)

    # Create seismic_interpretations table
    op.create_table('seismic_interpretations',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('dataset_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('interpretation_type', sa.String(length=50), nullable=False),
        sa.Column('geometry_data', sa.JSON(), nullable=True),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('opacity', sa.Float(), nullable=True),
        sa.Column('thickness', sa.Float(), nullable=True),
        sa.Column('confidence_level', sa.Float(), nullable=True),
        sa.Column('quality_score', sa.Float(), nullable=True),
        sa.Column('interpreter_id', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['dataset_id'], ['seismic_datasets.id'], ),
        sa.ForeignKeyConstraint(['interpreter_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_seismic_interpretations_id'), 'seismic_interpretations', ['id'], unique=False)

    # Create seismic_analyses table
    op.create_table('seismic_analyses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('dataset_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('analysis_type', sa.String(length=100), nullable=False),
        sa.Column('parameters', sa.JSON(), nullable=True),
        sa.Column('result_file_path', sa.String(length=500), nullable=True),
        sa.Column('result_metadata', sa.JSON(), nullable=True),
        sa.Column('algorithm_version', sa.String(length=50), nullable=True),
        sa.Column('processing_time', sa.Float(), nullable=True),
        sa.Column('cpu_usage', sa.Float(), nullable=True),
        sa.Column('memory_usage', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('progress', sa.Float(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('analyst_id', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['analyst_id'], ['users.id'], ),
        sa.ForeignKeyConstraint(['dataset_id'], ['seismic_datasets.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_seismic_analyses_id'), 'seismic_analyses', ['id'], unique=False)

    # Create seismic_attributes table
    op.create_table('seismic_attributes',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('dataset_id', sa.Integer(), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('attribute_type', sa.String(length=100), nullable=False),
        sa.Column('data_file_path', sa.String(length=500), nullable=True),
        sa.Column('computation_parameters', sa.JSON(), nullable=True),
        sa.Column('min_value', sa.Float(), nullable=True),
        sa.Column('max_value', sa.Float(), nullable=True),
        sa.Column('mean_value', sa.Float(), nullable=True),
        sa.Column('std_deviation', sa.Float(), nullable=True),
        sa.Column('computed_by', sa.Integer(), nullable=True),
        sa.Column('computed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['computed_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['dataset_id'], ['seismic_datasets.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_seismic_attributes_id'), 'seismic_attributes', ['id'], unique=False)

    # Create seismic_sessions table
    op.create_table('seismic_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('session_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('datasets', sa.JSON(), nullable=True),
        sa.Column('viewport_settings', sa.JSON(), nullable=True),
        sa.Column('display_settings', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('last_accessed', sa.DateTime(), nullable=True),
        sa.Column('is_shared', sa.Boolean(), nullable=True),
        sa.Column('shared_with', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_seismic_sessions_id'), 'seismic_sessions', ['id'], unique=False)

def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index(op.f('ix_seismic_sessions_id'), table_name='seismic_sessions')
    op.drop_table('seismic_sessions')
    
    op.drop_index(op.f('ix_seismic_attributes_id'), table_name='seismic_attributes')
    op.drop_table('seismic_attributes')
    
    op.drop_index(op.f('ix_seismic_analyses_id'), table_name='seismic_analyses')
    op.drop_table('seismic_analyses')
    
    op.drop_index(op.f('ix_seismic_interpretations_id'), table_name='seismic_interpretations')
    op.drop_table('seismic_interpretations')
    
    op.drop_index(op.f('ix_seismic_datasets_name'), table_name='seismic_datasets')
    op.drop_index(op.f('ix_seismic_datasets_id'), table_name='seismic_datasets')
    op.drop_table('seismic_datasets')
