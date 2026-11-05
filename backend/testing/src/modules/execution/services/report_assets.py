import asyncio
import hashlib
import io

from fastapi import HTTPException
from pymongo.errors import DuplicateKeyError

from src.clients.storage import storage_client
from src.core.common import get_project, new_id, now
from src.modules.execution.services.reporting import fail
from src.repositories.reporting import reporting_repository as repository


def image_ids(document):
    values = set()
    def visit(node):
        if node.get("type") == "image":
            values.add((node.get("attrs") or {}).get("asset_id"))
        for child in node.get("content", []):
            visit(child)
    visit(document)
    return values - {None, ""}


def normalize_image_urls(document, project_id, report_id=None):
    import copy
    value = copy.deepcopy(document)
    def visit(node):
        if node.get("type") == "image":
            asset_id = node["attrs"]["asset_id"]
            node["attrs"]["src"] = f"/api/kiem-thu/bao-cao-cong-viec/{report_id}/anh/{asset_id}" if report_id else f"/api/kiem-thu/du-an/{project_id}/bao-cao-cong-viec/anh/{asset_id}"
        for child in node.get("content", []):
            visit(child)
    visit(value)
    return value


def sanitize_image(data):
    from PIL import Image, ImageOps
    try:
        with Image.open(io.BytesIO(data)) as source:
            if source.width * source.height > 16_000_000 or source.format not in {"PNG", "JPEG"}:
                fail("REPORT_IMAGE_FORMAT_INVALID", 422)
            image = ImageOps.exif_transpose(source)
            image = image.convert("RGBA" if "A" in image.getbands() else "RGB")
            output = io.BytesIO()
            image.save(output, format="PNG")
            result = output.getvalue()
            if len(result) > 15 * 1024 * 1024:
                fail("REPORT_IMAGE_TOO_LARGE", 422)
            return result, image.width, image.height
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=422, detail={"code": "REPORT_IMAGE_INVALID"}) from error


async def upload_image(project_id, data, user):
    await get_project(project_id, user, "workreport.write")
    if not data or len(data) > 5 * 1024 * 1024:
        fail("REPORT_IMAGE_TOO_LARGE", 422)
    clean, width, height = await asyncio.to_thread(sanitize_image, data)
    digest = hashlib.sha256(clean).hexdigest()
    query = {"project_id": project_id, "created_by": user.id, "sha256": digest}
    existing = await repository.find("report_assets", query)
    if existing:
        return existing
    asset_id = new_id("RIMG")
    stored = await storage_client.store_report_asset(project_id, asset_id, "image.png", "image/png", clean)
    value = {"_id": asset_id, **query, "file": stored, "width": width, "height": height, "created_at": now(), "updated_at": now()}
    try:
        await repository.insert("report_assets", value)
    except DuplicateKeyError:
        return await repository.find("report_assets", query)
    return value


async def validate_asset_access(project_id, document, user, allowed_ids=()):
    for asset_id in image_ids(document):
        value = await repository.find("report_assets", {"_id": asset_id, "project_id": project_id})
        if not value or (value["created_by"] != user.id and asset_id not in allowed_ids):
            fail("REPORT_IMAGE_ACCESS_DENIED", 403)


async def export_assets(report):
    values = {}
    for asset_id in image_ids(report["content_doc"]):
        asset = await repository.find("report_assets", {"_id": asset_id, "project_id": report["project_id"]})
        if not asset:
            fail("REPORT_IMAGE_UNAVAILABLE", 422)
        values[asset_id] = await storage_client.read_report_asset(report["project_id"], asset_id, asset["file"]["object_key"])
    return values
