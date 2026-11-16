from fastapi import APIRouter, Depends

from src.core.dependency import verify_internal_token
from src.schemas.embedding import (
    BatchEmbeddingResponse,
    EmbedBatchRequest,
    EmbeddingResponse,
    EmbedQueryRequest,
)
from src.schemas.response import APIResponse
from src.services.embedding import embedder

router = APIRouter(dependencies=[Depends(verify_internal_token)])


@router.post(
    "/truy-van",
    response_model=APIResponse[EmbeddingResponse],
    description="Create an embedding for a knowledge query",
)
async def embed_single_query(req: EmbedQueryRequest):
    emb = await embedder.embed_query(req.text)
    return APIResponse(
        data=EmbeddingResponse(embedding=emb), message="Query embedding generated"
    )


@router.post(
    "/hang-loat",
    response_model=APIResponse[BatchEmbeddingResponse],
    description="Create embeddings for a batch of knowledge texts",
)
async def embed_batch_texts(req: EmbedBatchRequest):
    embs = await embedder.embed_batch(req.texts)
    return APIResponse(
        data=BatchEmbeddingResponse(embeddings=embs, count=len(embs)),
        message="Batch embeddings generated",
    )
