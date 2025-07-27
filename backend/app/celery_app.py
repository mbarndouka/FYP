from celery import Celery
import os
from dotenv import load_dotenv

load_dotenv()

# Redis configuration for Celery - Updated for Docker
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

# Initialize Celery
celery_app = Celery(
    "seismic_processing",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "app.tasks.seismic_tasks",
        "app.tasks.reservoir_tasks"
    ]
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Task routing
celery_app.conf.task_routes = {
    "app.tasks.seismic_tasks.process_seismic_analysis": {"queue": "seismic_processing"},
    "app.tasks.seismic_tasks.generate_visualization": {"queue": "visualization"},
    "app.tasks.reservoir_tasks.run_reservoir_simulation": {"queue": "reservoir_simulation"},
    "app.tasks.reservoir_tasks.run_predictive_analysis": {"queue": "predictive_analysis"},
}

if __name__ == "__main__":
    celery_app.start()
