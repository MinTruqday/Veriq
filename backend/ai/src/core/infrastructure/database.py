import asyncio

from loguru import logger

from src.core.infrastructure.configuration import settings


class DatabaseInfrastructure:
    def __init__(self):
        self.mongodb = None


database = DatabaseInfrastructure()


async def init_db():
    mongo_uri = settings.MONGODB_URI

    if not mongo_uri:
        logger.error("Failed to initialize database connection due to missing MongoDB URI")
        import sys

        sys.exit(1)

    from motor.motor_asyncio import AsyncIOMotorClient

    database.mongodb = AsyncIOMotorClient(mongo_uri)

    from src.core.infrastructure.mq import mq

    max_retries = 5
    for i in range(max_retries):
        try:
            if await mq.health_check():
                logger.info("RabbitMQ connection is stable")
                break
            else:
                raise Exception("MQ health check failed")
        except Exception as e:
            if i == max_retries - 1:
                logger.exception("RabbitMQ connection failed")
                raise e
            logger.exception("Retrying RabbitMQ connection")
            await asyncio.sleep(5)

    await setup_indexes()


async def setup_indexes():
    try:
        db = database.mongodb[settings.AI_DB_NAME]
        from pymongo import ASCENDING, DESCENDING, IndexModel

        index_sets = {
            "agent_traces": [
                IndexModel([("session_id", ASCENDING), ("started_at", DESCENDING)]),
                IndexModel([("status", ASCENDING), ("started_at", DESCENDING)]),
            ],
            "ai_sessions": [
                IndexModel([("user_id", ASCENDING), ("updated_at", DESCENDING)]),
                IndexModel([("user_id", ASCENDING), ("document_id", ASCENDING)]),
            ],
            "ai_messages": [
                IndexModel([("session_id", ASCENDING), ("created_at", ASCENDING)]),
                IndexModel([("user_id", ASCENDING), ("created_at", DESCENDING)]),
            ],
            "retrieval_audit": [
                IndexModel([("requester_id", ASCENDING), ("created_at", DESCENDING)]),
                IndexModel([("document_ids", ASCENDING), ("created_at", DESCENDING)]),
            ],
            "ai_workspaces": [
                IndexModel([("user_id", ASCENDING), ("updated_at", DESCENDING)]),
                IndexModel([("user_id", ASCENDING), ("status", ASCENDING)]),
            ],
            "agent_runs": [
                IndexModel([("project_id", ASCENDING), ("updated_at", DESCENDING)]),
                IndexModel([("user_id", ASCENDING), ("updated_at", DESCENDING)]),
                IndexModel([("status", ASCENDING), ("updated_at", DESCENDING)]),
                IndexModel(
                    [
                        ("project_id", ASCENDING),
                        ("requester_user_id", ASCENDING),
                        ("constraints.parent_automation_run_id", ASCENDING),
                        ("created_at", ASCENDING),
                    ],
                    name="automation_workflow_children",
                ),
            ],
            "automation_runs": [
                IndexModel([("project_id", ASCENDING), ("updated_at", DESCENDING)]),
                IndexModel([("requester_user_id", ASCENDING), ("updated_at", DESCENDING)]),
                IndexModel([("status", ASCENDING), ("updated_at", DESCENDING)]),
                IndexModel(
                    [("status", ASCENDING), ("worker_lease_expires_at", ASCENDING)],
                    name="automation_worker_lease_recovery_scan",
                ),
                IndexModel(
                    [
                        ("status", ASCENDING),
                        ("error_code", ASCENDING),
                        ("updated_at", ASCENDING),
                        ("_id", ASCENDING),
                    ],
                    name="automation_queue_recovery_scan",
                ),
                IndexModel(
                    [
                        ("trigger", ASCENDING),
                        ("source_event_id", ASCENDING),
                        ("status", ASCENDING),
                    ],
                    name="automation_document_revocation_scan",
                ),
                IndexModel(
                    [("project_id", ASCENDING), ("source_event_id", ASCENDING)],
                    unique=True,
                    name="one_automation_run_per_source_event",
                    partialFilterExpression={
                        "source_event_id": {"$type": "string"},
                    },
                ),
            ],
            "automation_definitions": [
                IndexModel([("project_id", ASCENDING), ("updated_at", DESCENDING)]),
                IndexModel([("project_id", ASCENDING), ("trigger", ASCENDING), ("enabled", ASCENDING)]),
                IndexModel(
                    [("project_id", ASCENDING), ("trigger", ASCENDING)],
                    unique=True,
                    name="one_enabled_automation_definition_per_trigger",
                    partialFilterExpression={"enabled": True},
                ),
            ],
            "automation_checkpoints": [
                IndexModel(
                    [
                        ("automation_run_id", ASCENDING),
                        ("checkpoint_sequence", ASCENDING),
                        ("created_at", ASCENDING),
                    ],
                    name="automation_run_checkpoint_sequence",
                ),
            ],
            "mcp_tool_call_audits": [
                IndexModel(
                    [("status", ASCENDING), ("started_at", ASCENDING)],
                    name="mcp_call_audit_interruption_recovery",
                ),
                IndexModel(
                    [("project_id", ASCENDING), ("completed_at", DESCENDING)],
                    name="project_mcp_call_audit_history",
                ),
                IndexModel(
                    [("automation_run_id", ASCENDING), ("completed_at", ASCENDING)],
                    name="automation_run_mcp_call_audit_history",
                ),
                IndexModel(
                    [
                        ("automation_run_id", ASCENDING),
                        ("task_id", ASCENDING),
                        ("completed_at", ASCENDING),
                    ],
                    name="automation_task_mcp_call_audit_history",
                ),
            ],
            "automation_source_facts": [
                IndexModel([("automation_run_id", ASCENDING), ("created_at", ASCENDING)]),
                IndexModel([("project_id", ASCENDING), ("artifact_version_id", ASCENDING)]),
            ],
            "automation_derivation_receipts": [
                IndexModel([("automation_run_id", ASCENDING)], unique=True),
                IndexModel([("project_id", ASCENDING), ("created_at", DESCENDING)]),
            ],
            "dead_letter_recovery_audit": [
                IndexModel(
                    [("created_at", DESCENDING), ("_id", ASCENDING)],
                    name="dead_letter_recovery_history",
                ),
                IndexModel(
                    [("status", ASCENDING), ("created_at", ASCENDING)],
                    name="dead_letter_recovery_pending_actions",
                ),
            ],
            "automation_project_blueprints": [
                IndexModel(
                    [("project_id", ASCENDING), ("version", ASCENDING)],
                    unique=True,
                    name="one_project_testability_blueprint_version",
                ),
                IndexModel(
                    [("project_id", ASCENDING), ("source_digest", ASCENDING)],
                    unique=True,
                    name="one_project_blueprint_per_compilation",
                ),
                IndexModel(
                    [("project_id", ASCENDING), ("automation_run_ids", ASCENDING)],
                    unique=True,
                    name="one_project_blueprint_per_automation_run",
                ),
            ],
            "testability_benchmark_datasets": [
                IndexModel(
                    [("created_at", DESCENDING), ("_id", ASCENDING)],
                    name="benchmark_dataset_history",
                ),
            ],
            "testability_benchmark_runs": [
                IndexModel(
                    [("dataset_id", ASCENDING), ("created_at", DESCENDING), ("_id", ASCENDING)],
                    name="benchmark_run_history",
                ),
            ],
            "document_ingestion_page_checkpoints": [
                IndexModel(
                    [
                        ("document_id", ASCENDING),
                        ("project_id", ASCENDING),
                        ("owner_id", ASCENDING),
                        ("source_hash", ASCENDING),
                        ("parser_name", ASCENDING),
                        ("parser_version", ASCENDING),
                        ("parser_contract_version", ASCENDING),
                        ("ocr_language", ASCENDING),
                        ("page_no", ASCENDING),
                    ],
                    unique=True,
                    name="one_checkpoint_per_document_source_parser_language_page",
                ),
                IndexModel(
                    [("expires_at", ASCENDING)],
                    expireAfterSeconds=0,
                    name="document_ingestion_page_checkpoint_ttl",
                ),
            ],
            "long_term_memory": [
                IndexModel([("project_id", ASCENDING), ("created_at", DESCENDING)]),
                IndexModel([("project_id", ASCENDING), ("trusted", ASCENDING)]),
                IndexModel(
                    [
                        ("project_id", ASCENDING),
                        ("owner_id", ASCENDING),
                        ("trusted", ASCENDING),
                        ("created_at", DESCENDING),
                    ]
                ),
                IndexModel([("run_id", ASCENDING)], unique=True),
            ],
        }
        for collection_name, indexes in index_sets.items():
            await db[collection_name].create_indexes(indexes)
        checkpoint_collection = db["document_ingestion_page_checkpoints"]
        existing_checkpoint_indexes = await checkpoint_collection.index_information()
        if "one_checkpoint_per_document_source_parser_page" in existing_checkpoint_indexes:
            await checkpoint_collection.drop_index(
                "one_checkpoint_per_document_source_parser_page"
            )
        logger.info("MongoDB index creation completed")
    except Exception:
        logger.exception("MongoDB index creation failed")
        raise


async def close_db():
    if database.mongodb:
        database.mongodb.close()
