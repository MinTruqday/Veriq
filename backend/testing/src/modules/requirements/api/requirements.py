from fastapi import APIRouter

from .requirement_analysis import router as analysis_router
from .requirement_documents import router as documents_router
from .requirement_imports import router as imports_router
from .requirement_records import router as records_router
from .requirement_templates import router as templates_router


router = APIRouter()
router.include_router(records_router)
router.include_router(analysis_router)
router.include_router(documents_router)
router.include_router(imports_router)
router.include_router(templates_router)
