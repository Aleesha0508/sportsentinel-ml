from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes.assets import router as assets_router
from app.routes.violations import router as violations_router
from app.routes.match import router as match_router
from app.routes.dashboard import router as dashboard_router
from app.routes.graph import router as graph_router
from app.routes.violation_view import router as violation_view_router
from app.routes.anomalies import router as anomalies_router
from app.routes.dmca import router as dmca_router
from app.routes.crawler import router as crawler_router

app = FastAPI(title="Sports Asset Protection API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

app.include_router(assets_router, prefix="/assets", tags=["assets"])
app.include_router(violations_router, prefix="/violations", tags=["violations"])
app.include_router(match_router, prefix="/match", tags=["match"])
app.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])
app.include_router(graph_router, prefix="/graph", tags=["graph"])
app.include_router(violation_view_router, prefix="/violations", tags=["violation-view"])
app.include_router(anomalies_router, prefix="/anomalies", tags=["anomalies"])
app.include_router(dmca_router, prefix="/dmca", tags=["dmca"])
app.include_router(crawler_router, prefix="/crawler", tags=["crawler"])