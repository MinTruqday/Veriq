PRIVATE_RETRIEVAL_METADATA_KEYS = frozenset(
    {
        "owner_id",
        "creator_id",
        "shared_with",
        "asset_key",
        "file_url",
        "source_url",
        "download_url",
        "presigned_url",
        "object_storage_url",
        "storage_url",
    }
)


def public_retrieval_metadata(value):
    if isinstance(value, dict):
        return {
            key: public_retrieval_metadata(item)
            for key, item in value.items()
            if key not in PRIVATE_RETRIEVAL_METADATA_KEYS
        }
    if isinstance(value, list):
        return [public_retrieval_metadata(item) for item in value]
    return value
