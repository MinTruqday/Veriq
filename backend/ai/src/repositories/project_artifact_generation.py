import asyncio
import hashlib
from datetime import datetime, timezone

from pymongo.errors import DuplicateKeyError

from src.core.infrastructure.configuration import settings
from src.core.infrastructure.database import database
from src.store.bm25 import bm25_store
from src.store.vector import vector_store


class ProjectArtifactGenerationConflict(RuntimeError):
    pass


class ProjectArtifactGenerationUnavailable(RuntimeError):
    pass


class ProjectArtifactGenerationRepository:
    collection_name = "project_artifact_index_manifests"
    legacy_generation = "LEGACY"

    @staticmethod
    def _manifest_id(project_id: str, artifact_version_id: str) -> str:
        identity = f"{project_id}\0{artifact_version_id}".encode("utf-8")
        return hashlib.sha256(identity).hexdigest()

    def _collection(self):
        if database.mongodb is None:
            raise ProjectArtifactGenerationUnavailable("mongodb_not_initialized")
        return database.mongodb[settings.AI_DB_NAME][self.collection_name]

    async def _legacy_manifest(self, project_id: str, artifact_version_id: str) -> dict:
        vector_points, bm25_points = await asyncio.gather(
            vector_store.list_artifact_version_points(project_id, artifact_version_id),
            bm25_store.list_artifact_version_points(project_id, artifact_version_id),
        )
        vector_by_generation = {}
        bm25_by_generation = {}
        for point in vector_points:
            generation = str(
                point.get("metadata", {}).get("index_generation") or self.legacy_generation
            )
            vector_by_generation.setdefault(generation, []).append(point)
        for point in bm25_points:
            generation = str(
                point.get("metadata", {}).get("index_generation") or self.legacy_generation
            )
            bm25_by_generation.setdefault(generation, []).append(point)

        coherent = []
        for generation in vector_by_generation.keys() & bm25_by_generation.keys():
            vector_ids = {str(point["id"]) for point in vector_by_generation[generation]}
            bm25_ids = {str(point["id"]) for point in bm25_by_generation[generation]}
            if vector_ids and vector_ids == bm25_ids:
                latest = max(
                    str(point.get("metadata", {}).get("indexed_at") or "")
                    for point in vector_by_generation[generation]
                )
                coherent.append((latest, generation, len(vector_ids)))

        if coherent:
            _, generation, point_count = max(coherent)
            status = "ACTIVE"
            active_generation = generation
        else:
            status = "REMOVED"
            active_generation = None
            point_count = 0
        return {
            "project_id": project_id,
            "artifact_version_id": artifact_version_id,
            "status": status,
            "active_generation": active_generation,
            "point_count": point_count,
            "revision": 1,
            "updated_at": datetime.now(timezone.utc),
            "migration_source": "coherent_existing_index" if coherent else "no_coherent_existing_index",
        }

    async def get_or_migrate(self, project_id: str, artifact_version_id: str) -> dict:
        collection = self._collection()
        manifest_id = self._manifest_id(project_id, artifact_version_id)
        manifest = await collection.find_one({"_id": manifest_id})
        if manifest:
            return manifest
        candidate = await self._legacy_manifest(project_id, artifact_version_id)
        candidate["_id"] = manifest_id
        try:
            await collection.insert_one(candidate)
            return candidate
        except DuplicateKeyError:
            manifest = await collection.find_one({"_id": manifest_id})
            if manifest:
                return manifest
            raise ProjectArtifactGenerationUnavailable("manifest_creation_race_unresolved")

    async def publish(
        self,
        manifest: dict,
        generation: str,
        point_count: int,
    ) -> bool:
        if manifest.get("status") == "DELETING":
            raise ProjectArtifactGenerationConflict("artifact_generation_is_being_removed")
        result = await self._collection().update_one(
            {
                "_id": manifest["_id"],
                "revision": manifest["revision"],
                "status": manifest["status"],
                "active_generation": manifest.get("active_generation"),
            },
            {
                "$set": {
                    "status": "ACTIVE",
                    "active_generation": generation,
                    "point_count": point_count,
                    "updated_at": datetime.now(timezone.utc),
                },
                "$inc": {"revision": 1},
            },
        )
        return result.modified_count == 1

    async def begin_removal(self, project_id: str, artifact_version_id: str) -> dict:
        for _ in range(8):
            manifest = await self.get_or_migrate(project_id, artifact_version_id)
            if manifest.get("status") == "DELETING":
                return manifest
            result = await self._collection().update_one(
                {
                    "_id": manifest["_id"],
                    "revision": manifest["revision"],
                    "status": manifest["status"],
                    "active_generation": manifest.get("active_generation"),
                },
                {
                    "$set": {
                        "status": "DELETING",
                        "active_generation": None,
                        "point_count": 0,
                        "updated_at": datetime.now(timezone.utc),
                    },
                    "$inc": {"revision": 1},
                },
            )
            if result.modified_count == 1:
                return await self._collection().find_one({"_id": manifest["_id"]})
        raise ProjectArtifactGenerationConflict("artifact_generation_changed_before_removal")

    async def finish_removal(self, manifest: dict) -> bool:
        result = await self._collection().update_one(
            {
                "_id": manifest["_id"],
                "revision": manifest["revision"],
                "status": "DELETING",
                "active_generation": None,
            },
            {
                "$set": {
                    "status": "REMOVED",
                    "updated_at": datetime.now(timezone.utc),
                },
                "$inc": {"revision": 1},
            },
        )
        if result.modified_count == 1:
            return True
        current = await self._collection().find_one({"_id": manifest["_id"]})
        return bool(current and current.get("status") == "REMOVED")

    async def removal_is_current(self, manifest: dict) -> bool:
        current = await self._collection().find_one(
            {"_id": manifest["_id"], "revision": manifest["revision"], "status": "DELETING"}
        )
        return current is not None

    async def active_generations(self, documents: list[dict]) -> dict[tuple[str, str], str | None]:
        identities = set()
        for document in documents:
            metadata = document.get("metadata") or document
            if metadata.get("document_id"):
                continue
            project_id = str(metadata.get("project_id") or "").strip()
            artifact_version_id = str(metadata.get("artifact_version_id") or "").strip()
            if project_id and artifact_version_id:
                identities.add((project_id, artifact_version_id))

        collection = self._collection()
        manifest_ids = {
            self._manifest_id(project_id, artifact_version_id): (project_id, artifact_version_id)
            for project_id, artifact_version_id in identities
        }
        manifests = []
        if manifest_ids:
            manifests = await collection.find(
                {"_id": {"$in": list(manifest_ids)}}
            ).to_list(length=len(manifest_ids))
        existing_manifest_ids = {str(item.get("_id")) for item in manifests}
        active = {}
        for manifest in manifests:
            generation = manifest.get("active_generation")
            if manifest.get("status") == "ACTIVE" and generation:
                identity = manifest_ids.get(str(manifest.get("_id")))
                if identity:
                    active[identity] = str(generation)
            else:
                identity = manifest_ids.get(str(manifest.get("_id")))
                if identity:
                    active[identity] = None
        for manifest_id, identity in manifest_ids.items():
            if manifest_id not in existing_manifest_ids:
                manifest = await self.get_or_migrate(*identity)
                generation = manifest.get("active_generation")
                active[identity] = (
                    str(generation)
                    if manifest.get("status") == "ACTIVE" and generation
                    else None
                )
        return active

    async def filter_active(self, documents: list[dict]) -> list[dict]:
        active = await self.active_generations(documents)
        filtered = []
        for document in documents:
            metadata = document.get("metadata") or document
            if metadata.get("document_id"):
                filtered.append(document)
                continue
            project_id = str(metadata.get("project_id") or "").strip()
            artifact_version_id = str(metadata.get("artifact_version_id") or "").strip()
            if not project_id and not artifact_version_id:
                filtered.append(document)
                continue
            if not project_id or not artifact_version_id:
                continue
            generation = active.get((project_id, artifact_version_id))
            point_generation = str(metadata.get("index_generation") or self.legacy_generation)
            if generation and point_generation == generation:
                filtered.append(document)
        return filtered


project_artifact_generation_repository = ProjectArtifactGenerationRepository()
