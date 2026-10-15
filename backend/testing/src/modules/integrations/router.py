from fastapi import APIRouter

from .api.api_artifacts import router as api_artifacts_router
from .api.automation_execution import internal_router as internal_automation_router
from .api.automation_execution import router as automation_execution_router
from .api.automation_scripts import router as automation_scripts_router
from .api.cicd import internal_router as internal_cicd_router
from .api.cicd import router as cicd_router
from .api.connectors import router as connectors_router
from .api.webhooks import internal_router as internal_webhooks_router
from .api.webhooks import router as webhooks_router
from .api.junit_import import router as junit_import_router


router = APIRouter()
router.include_router(automation_scripts_router)
router.include_router(connectors_router)
router.include_router(automation_execution_router)
router.include_router(internal_automation_router)
router.include_router(cicd_router)
router.include_router(internal_cicd_router)
router.include_router(api_artifacts_router)
router.include_router(webhooks_router)
router.include_router(internal_webhooks_router)
router.include_router(junit_import_router)
