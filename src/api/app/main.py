from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers import sos, incidents

app = FastAPI(
    title="FloodRescue API",
    version="1.0.0",
    description="Tier 1 academic MVP - see project_brief.md for scope.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sos.router)
app.include_router(incidents.router)


@app.get("/health")
def health():
    return {"status": "ok"}
