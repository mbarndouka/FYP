"""Add reservoir tables

Revision ID: 004_add_reservoir_tables
Revises: 003_add_seismic_tables
Create Date: 2025-01-23 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '004_add_reservoir_tables'
down_revision = '003_add_seismic_tables'
branch_labels = None
depends_on = None


def upgrade():
    # Create enum types
    reservoir_data_type_enum = postgresql.ENUM('HISTORICAL', 'REAL_TIME', 'SYNTHETIC', name='reservoirdatatype')
    reservoir_data_type_enum.create(op.get_bind())
    
    simulation_status_enum = postgresql.ENUM('PENDING', 'PROCESSING', 'COMPLETED', 'FAILED', name='simulationstatus')
    simulation_status_enum.create(op.get_bind())
    
    forecast_status_enum = postgresql.ENUM('DRAFT', 'PUBLISHED', 'ARCHIVED', name='forecaststatus')
    forecast_status_enum.create(op.get_bind())
    
    warning_level_enum = postgresql.ENUM('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='warninglevel')
    warning_level_enum.create(op.get_bind())

    # Create reservoir_data table
    op.create_table('reservoir_data',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('data_type', reservoir_data_type_enum, nullable=False),
        sa.Column('file_path', sa.String(length=500), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('metadata', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('location_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('time_range_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('time_range_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('uploaded_by', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_processed', sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reservoir_data_id'), 'reservoir_data', ['id'], unique=False)

    # Create reservoir_simulations table
    op.create_table('reservoir_simulations',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('reservoir_data_id', sa.String(), nullable=False),
        sa.Column('simulation_parameters', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('extraction_scenario', sa.String(length=255), nullable=False),
        sa.Column('status', simulation_status_enum, nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('results_path', sa.String(length=500), nullable=True),
        sa.Column('results_summary', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('visualization_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('created_by', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['reservoir_data_id'], ['reservoir_data.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reservoir_simulations_id'), 'reservoir_simulations', ['id'], unique=False)

    # Create reservoir_forecasts table
    op.create_table('reservoir_forecasts',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('simulation_id', sa.String(), nullable=False),
        sa.Column('model_type', sa.String(length=100), nullable=False),
        sa.Column('model_parameters', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('training_data_info', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('model_accuracy_metrics', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('forecast_data', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('confidence_intervals', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('forecast_horizon_days', sa.Integer(), nullable=False),
        sa.Column('predicted_production_rate', sa.Float(), nullable=True),
        sa.Column('predicted_reservoir_pressure', sa.Float(), nullable=True),
        sa.Column('estimated_recovery_factor', sa.Float(), nullable=True),
        sa.Column('status', forecast_status_enum, nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('published_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['simulation_id'], ['reservoir_simulations.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reservoir_forecasts_id'), 'reservoir_forecasts', ['id'], unique=False)

    # Create reservoir_warnings table
    op.create_table('reservoir_warnings',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('forecast_id', sa.String(), nullable=False),
        sa.Column('warning_type', sa.String(length=100), nullable=False),
        sa.Column('severity_level', warning_level_enum, nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('trigger_conditions', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('recommended_actions', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('predicted_occurrence_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('is_acknowledged', sa.Boolean(), nullable=True),
        sa.Column('acknowledged_by', sa.String(), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['acknowledged_by'], ['users.id'], ),
        sa.ForeignKeyConstraint(['forecast_id'], ['reservoir_forecasts.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reservoir_warnings_id'), 'reservoir_warnings', ['id'], unique=False)

    # Create prediction_sessions table
    op.create_table('prediction_sessions',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('session_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('data_sources', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('analysis_parameters', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('preprocessing_steps', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('ml_pipeline_config', postgresql.JSON(astext_type=sa.Text()), nullable=False),
        sa.Column('feature_engineering_steps', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('model_selection_criteria', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('session_results', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('generated_forecasts', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('generated_warnings', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('created_by', sa.String(), nullable=False),
        sa.Column('shared_with_users', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['created_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_prediction_sessions_id'), 'prediction_sessions', ['id'], unique=False)


def downgrade():
    # Drop tables
    op.drop_index(op.f('ix_prediction_sessions_id'), table_name='prediction_sessions')
    op.drop_table('prediction_sessions')
    op.drop_index(op.f('ix_reservoir_warnings_id'), table_name='reservoir_warnings')
    op.drop_table('reservoir_warnings')
    op.drop_index(op.f('ix_reservoir_forecasts_id'), table_name='reservoir_forecasts')
    op.drop_table('reservoir_forecasts')
    op.drop_index(op.f('ix_reservoir_simulations_id'), table_name='reservoir_simulations')
    op.drop_table('reservoir_simulations')
    op.drop_index(op.f('ix_reservoir_data_id'), table_name='reservoir_data')
    op.drop_table('reservoir_data')
    
    # Drop enum types
    op.execute('DROP TYPE IF EXISTS warninglevel')
    op.execute('DROP TYPE IF EXISTS forecaststatus')
    op.execute('DROP TYPE IF EXISTS simulationstatus')
    op.execute('DROP TYPE IF EXISTS reservoirdatatype')
