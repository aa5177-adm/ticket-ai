from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings

# router imports
from app.api.routes.tickets import tickets_router


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

# Register routers
app.include_router(tickets_router, prefix="/api/v1/auth", tags=["Auth"])