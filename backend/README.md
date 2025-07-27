# FastAPI Supabase Project

A minimal FastAPI application with Supabase integration and Docker support.

## Features

- FastAPI web framework
- Supabase database integration
- Docker containerization
- CRUD operations for items
- CORS enabled
- Environment variable configuration

## Setup

### Prerequisites

- Docker and Docker Compose
- Supabase account and project

### Environment Setup

1. Copy the example environment file:

   ```bash
   cp .env.example .env
   ```

2. Update the `.env` file with your Supabase credentials:
   ```
   SUPABASE_URL=your_supabase_project_url
   SUPABASE_KEY=your_supabase_anon_key
   ```

### Supabase Table Setup

Create a table named `items` in your Supabase database with the following SQL:

```sql
CREATE TABLE items (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## Running the Application

### Using Docker Compose (Recommended)

```bash
docker-compose up --build
```

### Using Docker

```bash
# Build the image
docker build -t fastapi-supabase .

# Run the container
docker run -p 8000:8000 --env-file .env fastapi-supabase
```

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
uvicorn main:app --reload
```

## API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /items/` - Get all items
- `POST /items/` - Create a new item
- `GET /items/{item_id}` - Get item by ID
- `PUT /items/{item_id}` - Update item by ID
- `DELETE /items/{item_id}` - Delete item by ID

## API Documentation

Once the application is running, you can access:

- Interactive API docs: http://localhost:8000/docs
- Alternative API docs: http://localhost:8000/redoc

## Example Usage

### Create an item

```bash
curl -X POST "http://localhost:8000/items/" \
     -H "Content-Type: application/json" \
     -d '{"name": "Test Item", "description": "A test item"}'
```

### Get all items

```bash
curl -X GET "http://localhost:8000/items/"
```

## Project Structure

```
backend/
├── main.py              # FastAPI application
├── requirements.txt     # Python dependencies
├── Dockerfile          # Docker configuration
├── docker-compose.yml  # Docker Compose configuration
├── .env.example        # Environment variables template
├── .gitignore          # Git ignore rules
└── README.md           # Project documentation
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test your changes
5. Submit a pull request
