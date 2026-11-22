from fastapi import APIRouter

from .api.analytics import router as analytics_router
from .api.changes import router as changes_router
from .api.reviews import router as reviews_router
from .api.traceability import router as traceability_router


router = APIRouter()
router.include_router(reviews_router)
router.include_router(traceability_router)
router.include_router(changes_router)
router.include_router(analytics_router)
