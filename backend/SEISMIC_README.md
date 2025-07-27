# Seismic Data Analysis System

A comprehensive geophysical data analysis platform built with FastAPI, featuring 3D visualization, advanced processing algorithms, and real-time collaboration tools.

## Features

### 🌊 Seismic Data Management

- **Multi-format Support**: Upload and process SEG-Y, HDF5, and other seismic data formats
- **Metadata Extraction**: Automatic extraction of spatial coordinates, sample rates, and acquisition parameters
- **Data Validation**: Built-in validation for seismic data integrity and format compliance
- **Version Control**: Track changes and maintain data lineage

### 🔬 Advanced Processing Algorithms

- **Noise Reduction**: Bandpass filtering, AGC, and statistical noise reduction
- **Seismic Migration**: Time and depth migration algorithms
- **Attribute Analysis**: Coherence, amplitude envelope, instantaneous frequency
- **3D Visualization**: Interactive 3D rendering with PyVista and Plotly
- **Background Processing**: Asynchronous processing with Celery

### 🎯 Interpretation Tools

- **Interactive Annotation**: Draw and edit horizons, faults, and geological features
- **Multi-user Collaboration**: Real-time sharing of interpretations
- **Quality Control**: Confidence scoring and interpretation validation
- **Export Capabilities**: Multiple export formats for integration with other tools

### 📊 Visualization & Analytics

- **3D Volume Rendering**: Full 3D seismic volume visualization
- **Multi-view Dashboard**: Inline, crossline, and time slice views
- **Attribute Displays**: Specialized visualizations for seismic attributes
- **Interactive Controls**: Real-time parameter adjustment and filtering

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │    │  Celery Worker  │    │  Redis Broker   │
│                 │    │                 │    │                 │
│ • REST API      │◄──►│ • Processing    │◄──►│ • Task Queue    │
│ • Authentication│    │ • Visualization │    │ • Results Cache │
│ • File Upload   │    │ • Analysis      │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Supabase DB   │    │  File Storage   │    │   Monitoring    │
│                 │    │                 │    │                 │
│ • User Data     │    │ • Seismic Files │    │ • Flower UI     │
│ • Metadata      │    │ • Results       │    │ • Logs          │
│ • Sessions      │    │ • Visualizations│    │ • Metrics       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Quick Start with Docker

### Prerequisites

- Docker Desktop
- Docker Compose
- At least 8GB RAM (16GB recommended for large datasets)

### 1. Clone and Setup

```bash
git clone <repository-url>
cd backend
```

### 2. Environment Configuration

Create a `.env` file:

```bash
cp env.template .env
```

Edit `.env` with your configuration:

```env
# Supabase Configuration
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_key
SUPABASE_DB_PASSWORD=your_db_password

# Database
DATABASE_URL=postgresql://postgres.xxx:password@host:5432/postgres

# Application
APP_NAME=Seismic Analysis Platform
DEBUG=True

# Redis & Celery
REDIS_URL=redis://redis:6379
CELERY_BROKER_URL=redis://redis:6379
CELERY_RESULT_BACKEND=redis://redis:6379
```

### 3. Run Setup Script

```bash
python setup_seismic_docker.py
```

Or manually:

```bash
# Build and start services
docker-compose up --build -d

# Check service status
docker-compose ps
```

### 4. Access Services

- **API**: http://localhost:8000
- **Documentation**: http://localhost:8000/docs
- **Monitoring**: http://localhost:5555 (Celery Flower)

## API Usage

### Upload Seismic Dataset

```bash
curl -X POST "http://localhost:8000/api/v1/seismic/datasets/upload" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@seismic_data.sgy" \
  -F "name=North Sea Survey" \
  -F "description=3D seismic survey from North Sea" \
  -F "file_format=segy"
```

### Start Analysis

```bash
curl -X POST "http://localhost:8000/api/v1/seismic/analysis" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "dataset_id": 1,
    "name": "Noise Reduction",
    "analysis_type": "noise_reduction",
    "parameters": {
      "filter_type": "bandpass",
      "low_freq": 5,
      "high_freq": 50
    }
  }'
```

### Generate 3D Visualization

```bash
curl -X POST "http://localhost:8000/api/v1/seismic/datasets/1/visualization" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "view_mode": "3d",
    "color_map": "seismic",
    "transparency": 0.1
  }'
```

## Processing Workflows

### 1. Geoscientist Workflow

```python
# 1. Login and authentication
POST /api/v1/auth/login

# 2. Upload seismic data
POST /api/v1/seismic/datasets/upload

# 3. Apply noise reduction
POST /api/v1/seismic/algorithms/noise-reduction

# 4. Generate 3D visualization
POST /api/v1/seismic/datasets/{id}/visualization

# 5. Create interpretations
POST /api/v1/seismic/interpretations

# 6. Save session
POST /api/v1/seismic/sessions
```

### 2. Advanced Processing

```python
# Compute seismic attributes
POST /api/v1/seismic/algorithms/attributes
{
  "dataset_id": 1,
  "parameters": {
    "attribute_type": "coherence",
    "window_size": 5
  }
}

# Apply migration
POST /api/v1/seismic/algorithms/migration
{
  "dataset_id": 1,
  "parameters": {
    "migration_type": "kirchhoff",
    "velocity_model": "constant",
    "aperture": 1000
  }
}
```

## Development

### Local Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start Redis
redis-server

# Start Celery worker
celery -A app.celery_app worker --loglevel=info

# Start API server
uvicorn app.main:app --reload
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

### Testing

```bash
# Run tests
python -m pytest tests/

# Run specific test
python -m pytest tests/test_seismic.py -v
```

## Monitoring and Troubleshooting

### Service Logs

```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f fastapi-app
docker-compose logs -f celery-worker
docker-compose logs -f redis
```

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# Redis status
docker exec -it backend_redis_1 redis-cli ping

# Database connection
curl http://localhost:8000/api/v1/auth/health
```

### Performance Monitoring

- **Celery Flower**: http://localhost:5555
- **Resource Usage**: `docker stats`
- **Disk Usage**: Check `/uploads` and `/processing` directories

## Deployment

### Production Considerations

1. **Security**: Use environment-specific secrets
2. **Scaling**: Configure Celery worker count based on CPU cores
3. **Storage**: Use external storage for large seismic files
4. **Monitoring**: Set up logging aggregation and alerting
5. **Backup**: Regular backup of database and critical files

### Docker Compose Production

```yaml
version: "3.8"
services:
  fastapi-app:
    build: .
    deploy:
      replicas: 2
    environment:
      - DEBUG=False
    # ... other production settings
```

## API Reference

### Authentication Endpoints

- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/logout` - User logout
- `GET /api/v1/auth/me` - Get current user

### Seismic Data Endpoints

- `GET /api/v1/seismic/datasets` - List datasets
- `POST /api/v1/seismic/datasets/upload` - Upload dataset
- `GET /api/v1/seismic/datasets/{id}` - Get dataset details
- `PUT /api/v1/seismic/datasets/{id}` - Update dataset
- `DELETE /api/v1/seismic/datasets/{id}` - Delete dataset

### Analysis Endpoints

- `POST /api/v1/seismic/analysis` - Create analysis job
- `GET /api/v1/seismic/analysis/{id}` - Get analysis status
- `GET /api/v1/seismic/datasets/{id}/analyses` - List dataset analyses

### Interpretation Endpoints

- `POST /api/v1/seismic/interpretations` - Create interpretation
- `GET /api/v1/seismic/datasets/{id}/interpretations` - List interpretations
- `PUT /api/v1/seismic/interpretations/{id}` - Update interpretation

### Visualization Endpoints

- `POST /api/v1/seismic/datasets/{id}/visualization` - Generate 3D viz
- `GET /api/v1/seismic/datasets/{id}/slice` - Get 2D slice

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes and add tests
4. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For technical support or questions, please:

1. Check the documentation
2. Search existing issues
3. Create a new issue with detailed information
4. Join our community discussions
