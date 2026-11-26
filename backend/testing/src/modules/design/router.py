from fastapi import APIRouter

from .api.templates import router as templates_router
from .api.test_analysis import router as test_analysis_router
from .api.test_design import router as test_design_router


router = APIRouter()
router.include_router(templates_router)
router.include_router(test_design_router)
router.include_router(test_analysis_router)
