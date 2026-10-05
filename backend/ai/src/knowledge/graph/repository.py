from src.knowledge.graph.client import graph_client


class GraphRepository:
    async def ensure_schema(self):
        await graph_client.execute(
            "CREATE CONSTRAINT artifact_scope IF NOT EXISTS FOR (artifact:Artifact) REQUIRE artifact.scope_id IS UNIQUE"
        )

    async def upsert_artifact(
        self, project_id, artifact_type, artifact_id, scope_id, properties=None, reference_ids=None
    ):
        values = dict(properties or {})
        values.update(
            {
                "project_id": project_id,
                "artifact_id": artifact_id,
                "artifact_type": artifact_type,
                "scope_id": scope_id,
                "reference_ids": list(dict.fromkeys(str(value) for value in reference_ids or [])),
            }
        )
        return await graph_client.execute(
            "MERGE (artifact:Artifact {scope_id: $scope_id}) "
            "SET artifact += $properties RETURN artifact.scope_id AS scope_id",
            {"scope_id": scope_id, "properties": values},
        )

    async def link(self, project_id, source_scope_id, target_identifier, reference_fields=None):
        return await graph_client.execute(
            "MATCH (source:Artifact {scope_id: $source_scope_id, project_id: $project_id}) "
            "MATCH (target:Artifact {project_id: $project_id}) "
            "WHERE source.scope_id <> target.scope_id "
            "AND $target_identifier IN [target.artifact_id, target.artifact_version_id] "
            "MERGE (source)-[relation:RELATED]->(target) "
            "SET relation.reference_fields = $reference_fields "
            "RETURN type(relation) AS relationship",
            {
                "project_id": project_id,
                "source_scope_id": source_scope_id,
                "target_identifier": str(target_identifier),
                "reference_fields": list(dict.fromkeys(reference_fields or [])),
            },
        )

    async def reconcile(self, project_id, scope_id, identifiers):
        values = list(dict.fromkeys(str(identifier) for identifier in identifiers if identifier))
        if not values:
            return []
        return await graph_client.execute(
            "MATCH (target:Artifact {scope_id: $scope_id, project_id: $project_id}) "
            "MATCH (source:Artifact {project_id: $project_id}) "
            "WHERE source.scope_id <> target.scope_id "
            "AND any(reference IN coalesce(source.reference_ids, []) WHERE reference IN $identifiers) "
            "MERGE (source)-[relation:RELATED]->(target) "
            "RETURN count(relation) AS relationships",
            {"project_id": project_id, "scope_id": scope_id, "identifiers": values},
        )

    async def delete_artifact_version(self, project_id, artifact_version_id):
        parents = await graph_client.read(
            "MATCH (parent:Artifact {project_id: $project_id})-[:RELATED]->"
            "(artifact:Artifact {project_id: $project_id}) "
            "WHERE artifact.artifact_version_id = $artifact_version_id "
            "AND parent.artifact_type = replace(artifact.artifact_type, '_version', '') "
            "RETURN DISTINCT parent.scope_id AS scope_id",
            {"project_id": project_id, "artifact_version_id": artifact_version_id},
        )
        removed = await graph_client.execute(
            "MATCH (artifact:Artifact {project_id: $project_id}) "
            "WHERE artifact.artifact_version_id = $artifact_version_id "
            "WITH collect(artifact) AS artifacts "
            "FOREACH (item IN artifacts | DETACH DELETE item) "
            "RETURN size(artifacts) AS removed",
            {"project_id": project_id, "artifact_version_id": artifact_version_id},
        )
        for parent in parents:
            await graph_client.execute(
                "MATCH (artifact:Artifact {project_id: $project_id, scope_id: $scope_id}) "
                "WHERE NOT (artifact)--() DELETE artifact",
                {"project_id": project_id, "scope_id": parent["scope_id"]},
            )
        return removed

    async def search(self, project_id, query, limit=20):
        matches = await graph_client.read(
            """
MATCH path=(source:Artifact {project_id: $project_id})-[*0..3]-(related:Artifact {project_id: $project_id})
WHERE toLower(coalesce(source.text, '') + ' ' + coalesce(source.title, '') + ' ' + coalesce(source.artifact_id, '')) CONTAINS toLower($query)
RETURN DISTINCT properties(source) AS artifact,
       [node IN nodes(path) | node.scope_id] AS relationship_path,
       length(path) AS distance
ORDER BY distance ASC
LIMIT $limit
""",
            {
                "project_id": project_id,
                "query": query,
                "limit": limit,
            },
        )
        return [
            {
                **(match.get("artifact") or {}),
                "relationship_path": match.get("relationship_path") or [],
                "distance": match.get("distance") or 0,
            }
            for match in matches
        ]


graph_repository = GraphRepository()
