from fastapi import APIRouter

from .api.data_sets import router as data_sets_router
from .api.design_suggestions import router as design_suggestions_router
from .api.templates import router as templates_router
from .api.test_analysis import router as test_analysis_router
from .api.test_adequacy import router as test_adequacy_router
from .api.test_design import router as test_design_router
from .api.test_strategy import router as test_strategy_router


router = APIRouter()
router.include_router(data_sets_router)
router.include_router(design_suggestions_router)
router.include_router(templates_router)
router.include_router(test_design_router)
router.include_router(test_strategy_router)
router.include_router(test_analysis_router)
router.include_router(test_adequacy_router)
