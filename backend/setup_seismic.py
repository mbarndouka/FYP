#!/usr/bin/env python3
"""
Seismic Data Analysis Setup Script for Docker
This script sets up the Docker environment for seismic data analysis.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"\n{description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description} completed successfully")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed:")
        print(f"Error: {e.stderr}")
        return False

def check_docker():
    """Check if Docker is installed and running"""
    try:
        result = subprocess.run("docker --version", shell=True, check=True, capture_output=True, text=True)
        print(f"✓ Docker is installed: {result.stdout.strip()}")
        
        result = subprocess.run("docker-compose --version", shell=True, check=True, capture_output=True, text=True)
        print(f"✓ Docker Compose is installed: {result.stdout.strip()}")
        
        # Check if Docker daemon is running
        result = subprocess.run("docker info", shell=True, check=True, capture_output=True, text=True)
        print("✓ Docker daemon is running")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Docker check failed: {e.stderr}")
        print("Please ensure Docker Desktop is installed and running")
        return False

def check_env_file():
    """Check if .env file exists"""
    env_file = Path(".env")
    if env_file.exists():
        print("✓ .env file found")
        return True
    else:
        print("✗ .env file not found")
        print("Please create a .env file with the required environment variables")
        print("You can use env.template as a reference")
        return False

def create_docker_directories():
    """Create directories that will be mounted as volumes"""
    directories = [
        "uploads/seismic",
        "processing/seismic/results",
        "processing/seismic/attributes", 
        "processing/seismic/visualizations",
        "cache/visualization",
        "logs"
    ]
    
    print("\nCreating Docker volume directories...")
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {directory}")

def setup_docker_environment():
    """Set up the Docker environment for seismic data analysis"""
    print("Setting up Seismic Data Analysis Docker Environment")
    print("=" * 60)
    
    # Check Docker installation
    if not check_docker():
        return False
    
    # Check environment file
    if not check_env_file():
        return False
    
    # Create necessary directories
    create_docker_directories()
    
    # Build and start services
    commands = [
        ("docker-compose down", "Stopping existing containers"),
        ("docker-compose build", "Building Docker images"),
        ("docker-compose up -d redis", "Starting Redis service"),
        ("docker-compose run --rm db-migration", "Running database migrations"),
        ("docker-compose up -d", "Starting all services"),
    ]
    
    for command, description in commands:
        if not run_command(command, description):
            if "migration" in command.lower():
                print("Warning: Database migrations may have failed. This is normal if tables already exist.")
            else:
                return False
    
    # Wait a moment for services to start
    print("\nWaiting for services to start...")
    import time
    time.sleep(10)
    
    # Check service status
    print("\nChecking service status...")
    run_command("docker-compose ps", "Service status")
    
    print("\n" + "=" * 60)
    print("Docker setup completed successfully!")
    print("\nServices running:")
    print("- FastAPI Application: http://localhost:8000")
    print("- API Documentation: http://localhost:8000/docs")
    print("- Celery Flower (Monitoring): http://localhost:5555")
    print("- Redis: localhost:6379")
    
    print("\nUseful Docker commands:")
    print("- View logs: docker-compose logs -f [service-name]")
    print("- Stop services: docker-compose down")
    print("- Restart services: docker-compose restart")
    print("- Rebuild and restart: docker-compose up --build -d")
    
    print("\nFor seismic data analysis:")
    print("- Upload seismic files (SEG-Y, HDF5) via POST /api/v1/seismic/datasets/upload")
    print("- Process data via POST /api/v1/seismic/analysis")
    print("- View 3D visualizations via POST /api/v1/seismic/datasets/{id}/visualization")
    print("- Monitor processing jobs at http://localhost:5555")
    
    return True

def show_usage():
    """Show usage information"""
    print("\nSeismic Data Analysis Docker Setup")
    print("=" * 40)
    print("Usage: python setup_seismic.py [command]")
    print("\nCommands:")
    print("  setup     - Set up the complete Docker environment")
    print("  build     - Build Docker images only")
    print("  start     - Start services")
    print("  stop      - Stop services")
    print("  restart   - Restart services")
    print("  logs      - Show service logs")
    print("  status    - Show service status")
    print("  clean     - Clean up containers and volumes")

def build_only():
    """Build Docker images only"""
    return run_command("docker-compose build", "Building Docker images")

def start_services():
    """Start Docker services"""
    commands = [
        ("docker-compose up -d", "Starting services"),
        ("docker-compose ps", "Service status")
    ]
    for command, description in commands:
        if not run_command(command, description):
            return False
    return True

def stop_services():
    """Stop Docker services"""
    return run_command("docker-compose down", "Stopping services")

def restart_services():
    """Restart Docker services"""
    commands = [
        ("docker-compose down", "Stopping services"),
        ("docker-compose up -d", "Starting services"),
    ]
    for command, description in commands:
        if not run_command(command, description):
            return False
    return True

def show_logs():
    """Show service logs"""
    return run_command("docker-compose logs -f", "Showing logs (Press Ctrl+C to exit)")

def show_status():
    """Show service status"""
    return run_command("docker-compose ps", "Service status")

def clean_up():
    """Clean up Docker containers and volumes"""
    commands = [
        ("docker-compose down -v", "Stopping services and removing volumes"),
        ("docker system prune -f", "Cleaning up Docker system"),
    ]
    for command, description in commands:
        run_command(command, description)
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2:
        setup_docker_environment()
    else:
        command = sys.argv[1].lower()
        
        if command == "setup":
            setup_docker_environment()
        elif command == "build":
            build_only()
        elif command == "start":
            start_services()
        elif command == "stop":
            stop_services()
        elif command == "restart":
            restart_services()
        elif command == "logs":
            show_logs()
        elif command == "status":
            show_status()
        elif command == "clean":
            clean_up()
        else:
            show_usage()
    
    for command, description in commands:
        if not run_command(command, description):
            return False
    
    # Create directories
    print("\nCreating directories...")
    create_directories()
    
    # Run database migrations
    if not run_command("alembic upgrade head", "Running database migrations"):
        print("Warning: Database migrations failed. Please check your database connection.")
    
    print("\n" + "=" * 50)
    print("Setup completed successfully!")
    print("\nNext steps:")
    print("1. Start Redis server: redis-server")
    print("2. Start Celery worker: celery -A app.celery_app worker --loglevel=info")
    print("3. Start the application: uvicorn app.main:app --reload")
    print("\nFor seismic data analysis:")
    print("- Upload seismic files (SEG-Y, HDF5) via the API")
    print("- Use the analysis endpoints to process data")
    print("- View 3D visualizations through the web interface")
    
    return True

if __name__ == "__main__":
    setup_environment()
