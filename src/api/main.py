"""Main FastAPI application."""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .health import router as health_router
from .projects import router as projects_router
from .organizations import router as organizations_router
from .billing import router as billing_router
from .webhooks import router as webhooks_router
from .middleware.request_tracking import RequestTrackingMiddleware
from .middleware.security import SecurityMiddleware, SecurityHeadersMiddleware
from src.api.routers import context
from src.utils.security import SecurityManager
from src.utils.redis_client import get_redis_client

# Initialize security manager
security_manager = SecurityManager(get_redis_client())

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI application.
    
    Handles startup and shutdown events.
    """
    # Startup
    try:
        # Any additional startup initialization
        yield
    finally:
        # Cleanup application resources
        pass

app = FastAPI(
    title="AI Dev Team API",
    # Disable OpenAPI docs for webhook endpoint
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add security middleware first
app.add_middleware(SecurityMiddleware, security_manager=security_manager)
app.add_middleware(SecurityHeadersMiddleware)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add request tracking middleware
app.add_middleware(RequestTrackingMiddleware)

# Include routers
app.include_router(health_router, prefix="/health")
app.include_router(projects_router)
app.include_router(organizations_router)
app.include_router(billing_router)
app.include_router(webhooks_router)
app.include_router(context.router)