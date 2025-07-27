"""Add data integration tables

Revision ID: 005_add_data_integration_tables
Revises: 004_add_reservoir_tables
Create Date: 2025-07-23 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '005_add_data_integration_tables'
down_revision = '004_add_reservoir_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Create file_type enum
    file_type_enum = postgresql.ENUM(
        'seismic_data', 'well_log', 'core_sample', 'production_data', 
        'reservoir_model', 'geological_map', 'report', 'image', 'document', 'other',
        name='filetype'
    )
    file_type_enum.create(op.get_bind())
    
    # Create file_status enum
    file_status_enum = postgresql.ENUM(
        'uploading', 'processing', 'completed', 'failed', 'quarantined',
        name='filestatus'
    )
    file_status_enum.create(op.get_bind())
    
    # Create processing_status enum
    processing_status_enum = postgresql.ENUM(
        'pending', 'in_progress', 'completed', 'failed', 'skipped',
        name='processingstatus'
    )
    processing_status_enum.create(op.get_bind())
    
    # Create data_files table
    op.create_table(
        'data_files',
        sa.Column('id', sa.String(), primary_key=True, index=True),
        sa.Column('original_filename', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=False),
        sa.Column('file_type', file_type_enum, nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('file_hash', sa.String(64), nullable=True),
        sa.Column('uploaded_by', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('upload_timestamp', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('status', file_status_enum, default='uploading'),
        sa.Column('processing_status', processing_status_enum, default='pending'),
        sa.Column('processing_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processing_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('processing_error', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('tags', sa.Text(), nullable=True),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('acquisition_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_public', sa.Boolean(), default=False),
        sa.Column('is_archived', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    
    # Create file_metadata table
    op.create_table(
        'file_metadata',
        sa.Column('id', sa.String(), primary_key=True, index=True),
        sa.Column('file_id', sa.String(), sa.ForeignKey('data_files.id'), nullable=False),
        sa.Column('width', sa.Integer(), nullable=True),
        sa.Column('height', sa.Integer(), nullable=True),
        sa.Column('duration', sa.Float(), nullable=True),
        sa.Column('sample_rate', sa.Float(), nullable=True),
        sa.Column('frequency_range', sa.String(100), nullable=True),
        sa.Column('coordinate_system', sa.String(100), nullable=True),
        sa.Column('custom_metadata', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    
    # Create file_access_logs table
    op.create_table(
        'file_access_logs',
        sa.Column('id', sa.String(), primary_key=True, index=True),
        sa.Column('file_id', sa.String(), sa.ForeignKey('data_files.id'), nullable=False),
        sa.Column('user_id', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('ip_address', sa.String(45), nullable=True),
        sa.Column('user_agent', sa.String(500), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    # Create file_shares table
    op.create_table(
        'file_shares',
        sa.Column('id', sa.String(), primary_key=True, index=True),
        sa.Column('file_id', sa.String(), sa.ForeignKey('data_files.id'), nullable=False),
        sa.Column('shared_by', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('shared_with', sa.String(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('permission', sa.String(20), default='read'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    # Create data_integration_jobs table
    op.create_table(
        'data_integration_jobs',
        sa.Column('id', sa.String(), primary_key=True, index=True),
        sa.Column('file_id', sa.String(), sa.ForeignKey('data_files.id'), nullable=False),
        sa.Column('job_type', sa.String(50), nullable=False),
        sa.Column('status', processing_status_enum, default='pending'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('config', sa.Text(), nullable=True),
        sa.Column('result', sa.Text(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    
    # Create indexes for better performance
    op.create_index('idx_data_files_uploaded_by', 'data_files', ['uploaded_by'])
    op.create_index('idx_data_files_file_type', 'data_files', ['file_type'])
    op.create_index('idx_data_files_status', 'data_files', ['status'])
    op.create_index('idx_data_files_created_at', 'data_files', ['created_at'])
    op.create_index('idx_data_files_file_hash', 'data_files', ['file_hash'])
    
    op.create_index('idx_file_metadata_file_id', 'file_metadata', ['file_id'])
    
    op.create_index('idx_file_access_logs_file_id', 'file_access_logs', ['file_id'])
    op.create_index('idx_file_access_logs_user_id', 'file_access_logs', ['user_id'])
    op.create_index('idx_file_access_logs_timestamp', 'file_access_logs', ['timestamp'])
    
    op.create_index('idx_file_shares_file_id', 'file_shares', ['file_id'])
    op.create_index('idx_file_shares_shared_with', 'file_shares', ['shared_with'])
    op.create_index('idx_file_shares_is_active', 'file_shares', ['is_active'])
    
    op.create_index('idx_data_integration_jobs_file_id', 'data_integration_jobs', ['file_id'])
    op.create_index('idx_data_integration_jobs_status', 'data_integration_jobs', ['status'])


def downgrade():
    # Drop indexes
    op.drop_index('idx_data_integration_jobs_status')
    op.drop_index('idx_data_integration_jobs_file_id')
    op.drop_index('idx_file_shares_is_active')
    op.drop_index('idx_file_shares_shared_with')
    op.drop_index('idx_file_shares_file_id')
    op.drop_index('idx_file_access_logs_timestamp')
    op.drop_index('idx_file_access_logs_user_id')
    op.drop_index('idx_file_access_logs_file_id')
    op.drop_index('idx_file_metadata_file_id')
    op.drop_index('idx_data_files_file_hash')
    op.drop_index('idx_data_files_created_at')
    op.drop_index('idx_data_files_status')
    op.drop_index('idx_data_files_file_type')
    op.drop_index('idx_data_files_uploaded_by')
    
    # Drop tables
    op.drop_table('data_integration_jobs')
    op.drop_table('file_shares')
    op.drop_table('file_access_logs')
    op.drop_table('file_metadata')
    op.drop_table('data_files')
    
    # Drop enums
    sa.Enum(name='processingstatus').drop(op.get_bind())
    sa.Enum(name='filestatus').drop(op.get_bind())
    sa.Enum(name='filetype').drop(op.get_bind())
