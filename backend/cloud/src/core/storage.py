import asyncio

import aioboto3
import brotli
from botocore.exceptions import ClientError
from loguru import logger

from src.core.infrastructure.configuration import settings

OBJECT_STORAGE_ENDPOINT = settings.OBJECT_STORAGE_ENDPOINT
OBJECT_STORAGE_ACCESS_KEY = settings.OBJECT_STORAGE_ACCESS_KEY
OBJECT_STORAGE_SECRET_KEY = settings.OBJECT_STORAGE_SECRET_KEY
OBJECT_STORAGE_PRIVATE_BUCKET = settings.OBJECT_STORAGE_PRIVATE_BUCKET
OBJECT_STORAGE_PUBLIC_BUCKET = settings.OBJECT_STORAGE_PUBLIC_BUCKET
OBJECT_STORAGE_LEGACY_BUCKET = settings.OBJECT_STORAGE_LEGACY_BUCKET
OBJECT_STORAGE_PUBLIC_URL = settings.OBJECT_STORAGE_PUBLIC_URL
OBJECT_STORAGE_REGION = settings.OBJECT_STORAGE_REGION


def should_brotli_compress(
    object_name: str, content_type: str, content_length: int, requested: bool = False
) -> bool:
    extension = object_name.rsplit(".", 1)[-1].lower() if "." in object_name else ""
    text_type = content_type.lower().startswith("text/") or content_type.lower() in {
        "application/json",
        "application/ld+json",
        "application/xml",
    }
    return content_length >= 1024 and (
        requested
        or text_type
        or extension
        in {item.strip().lower() for item in settings.COMPRESSIBLE_TEXT_EXTENSIONS.split(",") if item.strip()}
    )


def original_content_length(metadata: dict) -> int:
    if metadata.get("ContentEncoding") == "br":
        value = metadata.get("Metadata", {}).get("original-size")
        try:
            return int(value)
        except (TypeError, ValueError):
            return -1
    return int(metadata.get("ContentLength", -1))


def get_bucket(path: str) -> str:
    if path.startswith(("system/", "users/", "client/", "temp/")):
        return OBJECT_STORAGE_PRIVATE_BUCKET
    return OBJECT_STORAGE_PUBLIC_BUCKET


session = aioboto3.Session()
_storage_client = None


async def get_storage_client():
    global _storage_client
    if _storage_client is None:
        _storage_client = await session.client(
            "s3",
            endpoint_url=OBJECT_STORAGE_ENDPOINT,
            aws_access_key_id=OBJECT_STORAGE_ACCESS_KEY,
            aws_secret_access_key=OBJECT_STORAGE_SECRET_KEY,
            region_name=OBJECT_STORAGE_REGION,
        ).__aenter__()
    return _storage_client


async def close_storage_client():
    global _storage_client
    if _storage_client is not None:
        await _storage_client.__aexit__(None, None, None)
        _storage_client = None


async def initialize_bucket():
    storage_client = await get_storage_client()
    for bucket in dict.fromkeys([OBJECT_STORAGE_PRIVATE_BUCKET, OBJECT_STORAGE_PUBLIC_BUCKET]):
        try:
            await storage_client.head_bucket(Bucket=bucket)
        except ClientError:
            logger.info(f"Initializing storage bucket {bucket}")
            await storage_client.create_bucket(Bucket=bucket)
            logger.info(f"Storage bucket {bucket} initialized")
    if "r2.cloudflarestorage.com" in OBJECT_STORAGE_ENDPOINT:
        return
    await storage_client.put_bucket_lifecycle_configuration(
        Bucket=OBJECT_STORAGE_PRIVATE_BUCKET,
        LifecycleConfiguration={
            "Rules": [
                {
                    "ID": "expire-temporary-chat-files",
                    "Status": "Enabled",
                    "Filter": {"Prefix": "temp/"},
                    "Expiration": {"Days": 14},
                }
            ]
        },
    )


async def upload_file(
    file_content: bytes,
    object_name: str,
    content_type: str = "application/pdf",
    compress: bool = False,
) -> str:
    original_size = len(file_content)
    kwargs = {"Bucket": get_bucket(object_name), "Key": object_name, "ContentType": content_type}

    if should_brotli_compress(object_name, content_type, len(file_content), compress):
        compressed = await asyncio.to_thread(
            brotli.compress,
            file_content,
            quality=5,
        )
        if len(compressed) < len(file_content) * 0.95:
            file_content = compressed
            kwargs["ContentEncoding"] = "br"
            kwargs["Metadata"] = {"original-size": str(original_size)}

    kwargs["Body"] = file_content

    storage_client = await get_storage_client()
    await storage_client.put_object(**kwargs)
    return object_name


async def download_file(object_name: str) -> tuple[bytes, str]:
    storage_client = await get_storage_client()
    try:
        response = await storage_client.get_object(Bucket=get_bucket(object_name), Key=object_name)
    except ClientError as error:
        if error.response.get("Error", {}).get("Code") not in {"NoSuchKey", "404"}:
            raise
        response = await storage_client.get_object(
            Bucket=OBJECT_STORAGE_LEGACY_BUCKET, Key=object_name
        )
    content = await response["Body"].read()

    if response.get("ContentEncoding") == "br":
        content = await asyncio.to_thread(brotli.decompress, content)

    return content, response.get("ContentType", "application/octet-stream")


async def delete_file(object_name: str) -> None:
    storage_client = await get_storage_client()
    await storage_client.delete_object(
        Bucket=get_bucket(object_name), Key=object_name
    )


async def generate_presigned_url(object_name: str, expiration: int = 3600) -> str:
    storage_client = await get_storage_client()
    params = {"Bucket": get_bucket(object_name), "Key": object_name}

    response = await storage_client.generate_presigned_url(
        "get_object", Params=params, ExpiresIn=expiration
    )
    if OBJECT_STORAGE_PUBLIC_URL and OBJECT_STORAGE_ENDPOINT in response:
        response = response.replace(OBJECT_STORAGE_ENDPOINT, OBJECT_STORAGE_PUBLIC_URL)
    return response


async def generate_presigned_put_url(
    object_name: str, content_type: str, expiration: int = 3600
) -> str:
    storage_client = await get_storage_client()
    params = {"Bucket": get_bucket(object_name), "Key": object_name, "ContentType": content_type}

    response = await storage_client.generate_presigned_url(
        "put_object", Params=params, ExpiresIn=expiration
    )
    if OBJECT_STORAGE_PUBLIC_URL and OBJECT_STORAGE_ENDPOINT in response:
        response = response.replace(OBJECT_STORAGE_ENDPOINT, OBJECT_STORAGE_PUBLIC_URL)
    return response
