from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.endpoints import router
from app.api.layout import router as layout_router
from app.core.config import settings
from app.utils.cleanup import start_cleanup

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

# Set all CORS enabled origins
if settings.BACKEND_CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(router, prefix=settings.API_V1_STR)
app.include_router(layout_router, prefix=f"{settings.API_V1_STR}/layout", tags=["layout"])


@app.on_event("startup")
def on_startup():
    start_cleanup(settings.BASE_DIR)


@app.get("/")
def root():
    return {"message": "Welcome to Electricity Bill Recognition API"}
