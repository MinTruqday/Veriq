from fastapi import APIRouter

from .api.analytics import router as analytics_router
from .api.changes import router as changes_router
from .api.defect_prevention import router as defect_prevention_router
from .api.device_matrices import router as device_matrices_router
from .api.environment_incidents import router as environment_incidents_router
from .api.measurements import router as measurements_router
from .api.non_functional_testing import router as non_functional_testing_router
from .api.quality_evaluations import router as quality_evaluations_router
from .api.review_sessions import router as review_sessions_router
from .api.reviews import router as reviews_router
from .api.risk import router as risk_router
from .api.traceability import router as traceability_router


router = APIRouter()
router.include_router(reviews_router)
router.include_router(review_sessions_router)
router.include_router(measurements_router)
router.include_router(quality_evaluations_router)
router.include_router(defect_prevention_router)
router.include_router(environment_incidents_router)
router.include_router(non_functional_testing_router)
router.include_router(device_matrices_router)
router.include_router(traceability_router)
router.include_router(changes_router)
router.include_router(risk_router)
router.include_router(analytics_router)
