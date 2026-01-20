"""Main FastAPI application"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime
import logging

from app.config import settings
from app.database import connect_to_mongo, close_mongo_connection
from app.api.v1 import auth, users, products, orders, payments, returns, support, admin, store_config, email_templates, pickup_locations

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events"""
    # Startup
    logger.info("Starting up JollyTienda API...")
    await connect_to_mongo()
    logger.info("Application ready!")

    yield

    # Shutdown
    logger.info("Shutting down JollyTienda API...")
    await close_mongo_connection()
    logger.info("Shutdown complete!")


# Create FastAPI application
app = FastAPI(
    title="JollyTienda API",
    version="1.0.0",
    description="""
    Complete e-commerce API for JollyTienda platform.

    ## Features

    * **Authentication**: Passwordless magic link authentication with JWT
    * **Products**: Full CRUD operations for products and categories with stats & analytics
    * **Orders**: Shopping cart and order management with stock reservations & pickup locations
    * **Payments**: Stripe integration for checkout, payment processing, refunds & disputes
    * **Returns**: Complete returns management system with approval workflow
    * **Support**: Real-time chat support with polling and assignment
    * **Admin**: User and customer management, media uploads, database management, maintenance mode

    ## Authentication

    Most endpoints require authentication using JWT tokens.
    Include the token in the Authorization header:
    ```
    Authorization: Bearer <your_jwt_token>
    ```
    """,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoints
@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint to verify the API is running.
    """
    return {
        "success": True,
        "status": "healthy",
        "version": "1.0.0",
        "app": settings.app_name
    }


@app.get("/liveness", tags=["Health"])
async def liveness_probe():
    """
    Kubernetes liveness probe endpoint.
    Returns 200 if the application is alive.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/readiness", tags=["Health"])
async def readiness_probe():
    """
    Kubernetes readiness probe endpoint.
    Returns 200 if the application is ready to serve traffic.
    Checks database connectivity.
    """
    try:
        # Check database connection
        from app.database import database
        if database.db is not None:
            # Perform a simple database operation
            await database.db.command("ping")
            return {
                "status": "ready",
                "database": "connected",
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "status": "not ready",
                "database": "not connected",
                "timestamp": datetime.utcnow().isoformat()
            }, 503
    except Exception as e:
        logger.error(f"Readiness check failed: {str(e)}")
        return {
            "status": "not ready",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }, 503


@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint with API information.
    """
    return {
        "success": True,
        "message": "Welcome to JollyTienda API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
    }


# Include routers
app.include_router(
    auth.router,
    prefix="/api/auth",
    tags=["Authentication"]
)

app.include_router(
    users.router,
    prefix="/api/admin",
    tags=["Admin - Users"]
)

app.include_router(
    products.router,
    prefix="/api",
    tags=["Products"]
)

app.include_router(
    orders.router,
    prefix="/api",
    tags=["Orders & Carts"]
)

app.include_router(
    payments.router,
    prefix="/api/payments",
    tags=["Payments"]
)

app.include_router(
    returns.router,
    prefix="/api/admin",
    tags=["Returns"]
)

app.include_router(
    support.router,
    prefix="/api/support",
    tags=["Support"]
)

app.include_router(
    admin.router,
    prefix="/api/admin",
    tags=["Admin - Advanced"]
)

app.include_router(
    admin.router_public,
    prefix="",
    tags=["Public"]
)

app.include_router(
    store_config.router,
    prefix="/api/admin/store",
    tags=["Admin - Store Config"]
)

app.include_router(
    email_templates.router,
    prefix="/api/admin/store/email-templates",
    tags=["Admin - Email Templates"]
)

app.include_router(
    pickup_locations.router,
    prefix="/api/admin/store/pickup-locations",
    tags=["Admin - Pickup Locations"]
)


# Error handlers
@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Custom 404 handler"""
    return JSONResponse(
        status_code=404,
        content={
            "success": False,
            "error": "Not Found",
            "detail": "The requested resource was not found"
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Custom 500 handler"""
    logger.error(f"Internal server error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "Internal Server Error",
            "detail": "An unexpected error occurred. Please try again later."
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.debug,
        log_level="info"
    )
