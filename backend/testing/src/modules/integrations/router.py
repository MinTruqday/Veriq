from fastapi import APIRouter

from .api.api_artifacts import router as api_artifacts_router
from .api.automation_scripts import router as automation_scripts_router
from .api.junit_import import router as junit_import_router


router = APIRouter()
router.include_router(automation_scripts_router)
router.include_router(api_artifacts_router)
router.include_router(junit_import_router)
