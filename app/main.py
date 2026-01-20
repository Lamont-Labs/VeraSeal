"""Main application entry point.

Forces TZ=UTC at process start and starts FastAPI server.
"""
import os
import time

os.environ["TZ"] = "UTC"
if hasattr(time, "tzset"):
    time.tzset()

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.invariants.checks import verify_artifacts_dir_writable

ARTIFACTS_BASE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "artifacts")

app = FastAPI(
    title="VeraSeal",
    description="Deterministic evaluator that records decisions with verifiable proof",
    version="1.0.0",
)

app.include_router(router)

static_path = os.path.join(os.path.dirname(__file__), "web", "static")
if os.path.isdir(static_path):
    app.mount("/static", StaticFiles(directory=static_path), name="static")


@app.on_event("startup")
async def startup_event():
    """Verify invariants at startup."""
    os.makedirs(os.path.join(ARTIFACTS_BASE, "evaluations"), exist_ok=True)
    os.makedirs(os.path.join(ARTIFACTS_BASE, "manifests"), exist_ok=True)
    
    verify_artifacts_dir_writable(ARTIFACTS_BASE)


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.environ.get("PORT", "5000"))
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
    )
