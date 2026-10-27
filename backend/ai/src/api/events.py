import asyncio
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from loguru import logger

from src.core.dependency import require_system_admin, verify_internal_token
from src.runtime.events import AgentEvent, CronSchedule, EventType, cron_scheduler, event_processor
from src.runtime.queue_names import DEAD_LETTER_QUEUE, DOCUMENT_INGESTION_QUEUE
from src.schemas.events import (
    CreateScheduleRequest,
    DeadLetterRedriveRequest,
    ManualTriggerRequest,
    WebhookPayload,
)
from src.schemas.auth import CurrentUser

router = APIRouter(prefix="/su-kien")


@router.post("/moc-goi", dependencies=[Depends(verify_internal_token)])
async def receive_webhook(body: WebhookPayload):
    try:
        event_type_str = body.event_type.lower()
        event_type_map = {
            "webhook": EventType.WEBHOOK,
            "document_uploaded": EventType.DOCUMENT_UPLOADED,
            "user_query": EventType.USER_QUERY,
            "system_heartbeat": EventType.SYSTEM_HEARTBEAT,
            "document_deleted": EventType.DOCUMENT_DELETED,
            "user_registered": EventType.USER_REGISTERED,
        }
        event_type = event_type_map[event_type_str]

        if event_type is EventType.DOCUMENT_UPLOADED:
            from src.core.infrastructure.mq import mq

            document_id = str(body.payload.get("document_id") or "").strip()
            if not document_id:
                raise HTTPException(
                    status_code=422,
                    detail={"code": "DOCUMENT_ID_REQUIRED"},
                )
            event_id = str(uuid4())
            published = await mq.publish(
                DOCUMENT_INGESTION_QUEUE,
                {
                    **body.payload,
                    "event_id": event_id,
                    "document_id": document_id,
                    "user_id": str(body.payload.get("user_id") or ""),
                    "superseded_document_id": str(
                        body.payload.get("superseded_document_id") or ""
                    ),
                    "attempt": 0,
                },
            )
            if not published:
                raise HTTPException(
                    status_code=503,
                    detail={"code": "DOCUMENT_INGESTION_QUEUE_UNAVAILABLE"},
                )
            return {
                "status": "accepted",
                "event_id": event_id,
                "event_type": event_type.value,
            }

        event = AgentEvent(
            event_id=str(uuid4()),
            event_type=event_type,
            payload=body.payload,
            source=body.source,
        )

        try:
            await event_processor.emit_event(event)
        except asyncio.QueueFull:
            raise HTTPException(status_code=503, detail={"code": "event_queue_full"})
        logger.info(f"Webhook received event_id={event.event_id}, type={event_type.value}")

        return {"status": "accepted", "event_id": event.event_id, "event_type": event_type.value}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Webhook processing error")
        raise HTTPException(status_code=500, detail={"code": "webhook_processing_failed"})


@router.post("/moc-goi/tai-lieu-dang-tai", dependencies=[Depends(verify_internal_token)])
async def document_uploaded_webhook(
    document_id: str,
    user_id: str = "",
    superseded_document_id: str = "",
    event_id: str = "",
):
    from src.core.infrastructure.mq import mq

    document_id = document_id.strip()
    if not document_id:
        raise HTTPException(
            status_code=422,
            detail={"code": "DOCUMENT_ID_REQUIRED"},
        )
    event_id = event_id.strip() or str(uuid4())
    published = await mq.publish(
        DOCUMENT_INGESTION_QUEUE,
        {
            "event_id": event_id,
            "document_id": document_id,
            "user_id": user_id,
            "superseded_document_id": superseded_document_id,
            "attempt": 0,
        },
    )
    if not published:
        raise HTTPException(
            status_code=503, detail={"code": "DOCUMENT_INGESTION_QUEUE_UNAVAILABLE"}
        )
    return {"status": "accepted", "event_id": event_id}


@router.get("/lich-trinh", dependencies=[Depends(require_system_admin)])
async def list_schedules():
    return {"schedules": cron_scheduler.list_schedules(), "total": len(cron_scheduler._schedules)}


@router.post("/lich-trinh", dependencies=[Depends(require_system_admin)])
async def create_schedule(req: CreateScheduleRequest):
    event_type_map = {
        "system_heartbeat": EventType.SYSTEM_HEARTBEAT,
        "document_uploaded": EventType.DOCUMENT_UPLOADED,
        "user_query": EventType.USER_QUERY,
        "webhook": EventType.WEBHOOK,
    }
    event_type = event_type_map.get(req.event_type, EventType.SYSTEM_HEARTBEAT)

    schedule = CronSchedule(
        schedule_id=str(uuid4()),
        name=req.name,
        cron_expression=f"*/{req.interval_seconds // 60 or 1} * * * *",
        interval_seconds=req.interval_seconds,
        event_type=event_type,
        payload_template=req.payload_template,
        enabled=req.enabled,
    )
    cron_scheduler.register(schedule)

    if cron_scheduler._running and schedule.enabled:
        schedule._task = asyncio.create_task(
            cron_scheduler._run_schedule(schedule), name=f"cron:{schedule.name}"
        )

    return {
        "status": "created",
        "schedule_id": schedule.schedule_id,
        "name": schedule.name,
        "interval_seconds": schedule.interval_seconds,
    }


@router.delete("/lich-trinh/{schedule_id}", dependencies=[Depends(require_system_admin)])
async def delete_schedule(schedule_id: str):
    if schedule_id not in cron_scheduler._schedules:
        raise HTTPException(status_code=404, detail={"code": "schedule_not_found"})
    cron_scheduler.unregister(schedule_id)
    return {"status": "deleted", "schedule_id": schedule_id}


@router.patch(
    "/lich-trinh/{schedule_id}/trang-thai", dependencies=[Depends(require_system_admin)]
)
async def toggle_schedule(schedule_id: str):
    schedule = cron_scheduler._schedules.get(schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail={"code": "schedule_not_found"})
    cron_scheduler.set_enabled(schedule_id, not schedule.enabled)
    return {"schedule_id": schedule_id, "name": schedule.name, "enabled": schedule.enabled}


@router.get("/trang-thai", dependencies=[Depends(require_system_admin)])
async def event_loop_status():
    return event_processor.get_stats()


@router.get("/lich-su", dependencies=[Depends(require_system_admin)])
async def event_history(limit: int = Query(default=20, ge=1, le=200)):
    return {"events": event_processor.get_recent_events(limit=limit)}


@router.get("/cap-nhat", dependencies=[Depends(require_system_admin)])
async def system_updates(limit: int = Query(default=20, ge=1, le=200)):
    updates = event_processor.update_registry.get_recent(limit=limit)
    return {
        "updates": [
            {
                "update_id": u.update_id,
                "event_id": u.event_id,
                "update_type": u.update_type,
                "description": u.description,
                "applied_at": u.applied_at.isoformat(),
                "success": u.success,
            }
            for u in updates
        ],
        "stats": event_processor.update_registry.get_stats(),
    }


@router.get("/hang-chet", dependencies=[Depends(require_system_admin)])
async def dead_letter_status():
    from src.services.dead_letter_recovery import dead_letter_recovery

    return {
        "queue": DEAD_LETTER_QUEUE,
        "pending_messages": await dead_letter_recovery.depth(),
    }


@router.get("/hang-chet/nhat-ky", dependencies=[Depends(require_system_admin)])
async def dead_letter_audit(limit: int = Query(default=50, ge=1, le=200)):
    from src.services.dead_letter_recovery import dead_letter_recovery

    return {"actions": await dead_letter_recovery.list_audit(limit=limit)}


@router.post("/hang-chet/phat-lai", dependencies=[Depends(require_system_admin)])
async def redrive_dead_letters(
    req: DeadLetterRedriveRequest,
    current_user: CurrentUser = Depends(require_system_admin),
):
    from src.services.dead_letter_recovery import dead_letter_recovery

    try:
        return await dead_letter_recovery.redrive(
            limit=req.limit,
            requested_by=str(current_user.id),
        )
    except Exception as error:
        logger.error("Dead-letter redrive failed error_type={}", type(error).__name__)
        raise HTTPException(
            status_code=503,
            detail={"code": "DEAD_LETTER_REDRIVE_UNAVAILABLE"},
        )


@router.post("/kich-hoat/{event_type}", dependencies=[Depends(require_system_admin)])
async def manual_trigger(
    event_type: Literal["heartbeat", "document_uploaded", "user_query"],
    req: ManualTriggerRequest = Body(default_factory=ManualTriggerRequest),
):
    event_type_map = {
        "heartbeat": EventType.SYSTEM_HEARTBEAT,
        "document_uploaded": EventType.DOCUMENT_UPLOADED,
        "user_query": EventType.USER_QUERY,
    }
    et = event_type_map[event_type]
    event = AgentEvent(
        event_id=str(uuid4()), event_type=et, payload=req.payload, source="manual_trigger"
    )
    result = await event_processor.handle_event(event)
    if event.error:
        raise HTTPException(
            status_code=503,
            detail={"code": "EVENT_HANDLER_FAILED", "message": event.error},
        )
    return {"status": "triggered", "event_id": event.event_id, "result": result}
