from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, protected, data_integration, seismic, reservoir

# Initialize FastAPI app
app = FastAPI(
    title="FastAPI Supabase App",
    description="A simple FastAPI application with Supabase integration",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(protected.router)
app.include_router(data_integration.router)
app.include_router(seismic.router)
app.include_router(reservoir.router)

# Basic routes
@app.get("/")
async def root():
    return {"message": "Hello World! FastAPI with Supabase is running."}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API is running"}