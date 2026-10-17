from fastapi import APIRouter

from .api.attachments import router as attachments_router
from .api.collaboration import router as collaboration_router
from .api.projects import router as projects_router
from .api.work_items import router as work_items_router


router = APIRouter()
router.include_router(projects_router)
router.include_router(work_items_router)
router.include_router(collaboration_router)
router.include_router(attachments_router)
