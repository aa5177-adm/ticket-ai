from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

# router imports
from app.api.routes.tickets import tickets_router
from app.api.routes.webhooks import webhook_router
# from app.api.routes.agent_endpoints import router as agent_router


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.API_VERSION,
    description="AI Powered ServiceNow Ticket Assignment System",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Restrict for prod
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers=["*"]
)

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint for load balancers and monitoring"""
    return {
        "status": "healthy",
        "service": "ticket-ai",
        "version": settings.API_VERSION
    }

# Register routers
app.include_router(tickets_router, prefix="/api/v1/auth", tags=["Auth"])
# app.include_router(agent_router, prefix="/api/v1", tags=["AI Agents"])

app.include_router(webhook_router, prefix="/api/v1", tags=["ServiceNow Webhook"])