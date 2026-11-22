from fastapi import APIRouter

from .api.access import router as access_router
from .api.attachments import router as attachments_router
from .api.collaboration import router as collaboration_router
from .api.projects import router as projects_router


router = APIRouter()
router.include_router(access_router)
router.include_router(projects_router)
router.include_router(collaboration_router)
router.include_router(attachments_router)
