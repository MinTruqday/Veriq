from fastapi import APIRouter

from .api.simple_reports import router as simple_reports_router
from .api.execution import router as execution_router
from .api.execution_context import router as execution_context_router
from .api.plan_progress import router as plan_progress_router
from .api.test_periods import router as test_periods_router


router = APIRouter()
router.include_router(simple_reports_router)
router.include_router(execution_router)
router.include_router(execution_context_router)
router.include_router(plan_progress_router)
router.include_router(test_periods_router)
