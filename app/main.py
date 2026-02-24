from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.api.tasks import router as tasks_router
from app.core.config import settings
from app.core.logging import logger
from app.services.task_queue import task_queue


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle"""
    # Startup
    logger.info("Starting Distributed Task Processing System")
    await task_queue.initialize()
    
    # Try to initialize Redis queue
    try:
        from app.services.redis_queue import redis_queue
        await redis_queue.initialize()
        logger.info("Redis queue initialized")
    except Exception as e:
        logger.warning(f"Redis not available, using in-memory queue: {str(e)}")
    
    logger.info("Task queue initialized")
    yield
    # Shutdown
    logger.info("Shutting down Distributed Task Processing System")
    
    # Close Redis connection if available
    try:
        from app.services.redis_queue import redis_queue
        await redis_queue.close()
    except:
        pass


# Create FastAPI app
app = FastAPI(
    title="Distributed Task Processing System",
    description="A system for processing long-running tasks asynchronously",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tasks_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Distributed Task Processing System",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "database": "connected",
        "queue": "ready"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug
    )
