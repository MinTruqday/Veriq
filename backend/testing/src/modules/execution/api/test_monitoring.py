from fastapi import APIRouter, Depends, Query

from src.core.auth import CurrentUser, get_current_user
from src.core.common import envelope
from src.schemas.test_monitoring import (
    ControlActionCreate,
    ControlActionPatch,
    ExitCriterionOverride,
    MonitoringSnapshotCreate,
    QualityDecisionCreate,
)
from src.modules.execution.services.test_monitoring import (
    create_control_action,
    create_monitoring_snapshot,
    get_live_plan_progress,
    create_quality_decision,
    export_quality_gate,
    get_quality_gate,
    get_snapshot_for_user,
    list_actions_for_user,
    list_monitoring_snapshots,
    list_quality_decisions,
    override_exit_criterion,
    update_control_action,
)

router = APIRouter(prefix="/kiem-thu", tags=["Giám sát và điều khiển kiểm thử"])


@router.get("/du-an/{project_id}/ke-hoach-kiem-thu/{plan_id}/tien-do")
async def get_plan_progress(project_id: str, plan_id: str, user: CurrentUser = Depends(get_current_user)):
    return envelope(await get_live_plan_progress(project_id, plan_id, user))


@router.get("/du-an/{project_id}/giam-sat-kiem-thu")
async def list_test_monitoring_snapshots(
    project_id: str,
    test_plan_id: str = Query(default="", max_length=200),
    release_id: str = Query(default="", max_length=200),
    limit: int = Query(default=100, ge=1, le=500),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(
        await list_monitoring_snapshots(
            project_id, test_plan_id or None, release_id or None, limit, user
        )
    )


@router.post("/du-an/{project_id}/giam-sat-kiem-thu/anh-chup", status_code=201)
async def create_test_monitoring_snapshot(
    project_id: str,
    payload: MonitoringSnapshotCreate,
    user: CurrentUser = Depends(get_current_user),
):
    value = await create_monitoring_snapshot(project_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.get("/giam-sat-kiem-thu/anh-chup/{snapshot_id}")
async def get_test_monitoring_snapshot(
    snapshot_id: str, user: CurrentUser = Depends(get_current_user)
):
    value = await get_snapshot_for_user(snapshot_id, user)
    return envelope(value, revision=value["revision"])


@router.post("/giam-sat-kiem-thu/anh-chup/{snapshot_id}/ghi-de-tieu-chi")
async def override_test_monitoring_exit_criterion(
    snapshot_id: str, payload: ExitCriterionOverride, user: CurrentUser = Depends(get_current_user)
):
    value = await override_exit_criterion(snapshot_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.get("/du-an/{project_id}/hanh-dong-dieu-khien")
async def list_test_control_actions(
    project_id: str,
    snapshot_id: str = Query(default="", max_length=200),
    status: str = Query(default="", max_length=30),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(
        await list_actions_for_user(project_id, snapshot_id or None, status or None, user)
    )


@router.post("/du-an/{project_id}/hanh-dong-dieu-khien", status_code=201)
async def create_test_control_action(
    project_id: str, payload: ControlActionCreate, user: CurrentUser = Depends(get_current_user)
):
    value = await create_control_action(project_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.patch("/hanh-dong-dieu-khien/{action_id}")
async def patch_test_control_action(
    action_id: str, payload: ControlActionPatch, user: CurrentUser = Depends(get_current_user)
):
    value = await update_control_action(action_id, payload, user)
    return envelope(value, revision=value["revision"])


@router.get("/giam-sat-kiem-thu/anh-chup/{snapshot_id}/danh-gia-chat-luong")
async def get_quality_gate_evaluation(
    snapshot_id: str, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await get_quality_gate(snapshot_id, user))


@router.get("/du-an/{project_id}/quyet-dinh-chat-luong")
async def list_quality_decision_history(
    project_id: str,
    release_id: str = Query(default="", max_length=200),
    user: CurrentUser = Depends(get_current_user),
):
    return envelope(await list_quality_decisions(project_id, release_id or None, user))


@router.post("/giam-sat-kiem-thu/anh-chup/{snapshot_id}/quyet-dinh-chat-luong", status_code=201)
async def record_quality_decision(
    snapshot_id: str, payload: QualityDecisionCreate, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await create_quality_decision(snapshot_id, payload, user))


@router.get("/giam-sat-kiem-thu/anh-chup/{snapshot_id}/xuat-bang-chung")
async def export_quality_gate_evidence(
    snapshot_id: str, user: CurrentUser = Depends(get_current_user)
):
    return envelope(await export_quality_gate(snapshot_id, user))
