from fastapi import APIRouter

from .api.execution import router as execution_router
from .api.execution_context import router as execution_context_router
from .api.test_completion import router as test_completion_router
from .api.test_monitoring import router as test_monitoring_router
from .api.test_status_reports import router as test_status_reports_router


router = APIRouter()
router.include_router(execution_router)
router.include_router(execution_context_router)
router.include_router(test_monitoring_router)
router.include_router(test_status_reports_router)
router.include_router(test_completion_router)
