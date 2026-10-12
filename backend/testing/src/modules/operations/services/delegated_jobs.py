from fastapi import HTTPException

from src.clients.worker import WorkerClientError, worker_client
from src.core.auth import CurrentUser
from src.core.common import get_project
from src.schemas.contracts.utility import DelegatedJobEnqueueInput


class DelegatedJobService:
    @staticmethod
    async def enqueue(project_id: str, input: DelegatedJobEnqueueInput, user: CurrentUser):
        event = input.event
        if event == "impact.analysis.requested":
            await get_project(project_id, user, "impact.execute")
        elif event == "duplicate.scan.requested":
            await get_project(project_id, user, "ai.run_duplicate_check")
        elif event == "test.generate.requested":
            await get_project(project_id, user, "ai.generate_testcase")
        elif event == "requirement.semantic_diff.requested":
            await get_project(project_id, user, "changeset.create")
        elif event == "knowledge.index.requested":
            await get_project(project_id, user, "knowledge.manage")
        else:
            await get_project(project_id, user, "requirement_document.extract")
        job = {
            "event": event,
            "project_id": project_id,
            "artifact_version_id": input.artifact_version_id,
            "model_version": input.model_version,
            "requester_id": user.id,
            "requester_email": user.email,
            "payload": input.payload,
        }
        try:
            return await worker_client.enqueue(job)
        except WorkerClientError as error:
            raise HTTPException(
                status_code=503, detail={"code": 'WORKER_UNAVAILABLE'}
            ) from error

    @staticmethod
    async def get(job_id: str, user: CurrentUser):
        
        try:
            job = await worker_client.get(job_id)
        except WorkerClientError as error:
            if error.status_code == 404:
                raise HTTPException(
                    status_code=404, detail={"code": 'JOB_NOT_FOUND'}
                ) from error
            raise HTTPException(
                status_code=503, detail={"code": 'WORKER_UNAVAILABLE'}
            ) from error
        project = await get_project(job.get("project_id", ""), user, "project.read")
        return {**job, "project_id": project["_id"]}
