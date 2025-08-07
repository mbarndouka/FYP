FROM python:3.10-slim-bookworm

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies for seismic data processing
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        gcc \
        g++ \
        gfortran \
        libopenblas-dev \
        liblapack-dev \
        pkg-config \
        libffi-dev \
        libssl-dev \
        libhdf5-dev \
        libnetcdf-dev \
        libblas-dev \
        libatlas-base-dev \
        python3-dev \
        redis-server \
        wget \
        curl \
        git \
        vim \
    && rm -rf /var/lib/apt/lists/*

# Install VTK dependencies for 3D visualization
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1-mesa-glx \
    libxrender1 \
    libsm6 \
    libxext6 \
    libglib2.0-0 \
    xvfb \
    python3-pyqt5 \
    python3-pyqt5.qtwebkit \
    libvtk9-dev \
    && rm -rf /var/lib/apt/lists/*


# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip setuptools wheel cython uv
RUN uv pip install --no-cache-dir -r requirements.txt --system

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p uploads/seismic \
    && mkdir -p processing/seismic/results \
    && mkdir -p processing/seismic/attributes \
    && mkdir -p processing/seismic/visualizations \
    && mkdir -p cache/visualization \
    && mkdir -p logs

# Set permissions
RUN chmod +x setup_seismic.py

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
