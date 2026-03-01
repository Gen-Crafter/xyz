import logging
from fastapi import APIRouter, Request, UploadFile, File, Form
from app.models.schemas import RAGIngestRequest, RAGQueryRequest, RAGQueryResult, RAGCollectionStats

logger = logging.getLogger("aigp.rag")
router = APIRouter(prefix="/rag", tags=["RAG Knowledge Base"])


@router.post("/ingest")
async def ingest_documents(data: RAGIngestRequest, request: Request):
    rag = request.app.state.rag_service
    result = await rag.ingest_regulation_texts()
    return result


@router.get("/collections", response_model=list[RAGCollectionStats])
async def list_collections(request: Request):
    rag = request.app.state.rag_service
    stats = await rag.get_collection_stats()
    return [RAGCollectionStats(**s) for s in stats]


@router.post("/query", response_model=RAGQueryResult)
async def query_rag(data: RAGQueryRequest, request: Request):
    rag = request.app.state.rag_service
    result = await rag.query_with_synthesis(
        query=data.query,
        regulations_filter=data.regulations_filter,
        top_k=data.top_k,
    )
    return RAGQueryResult(**result)


@router.post("/upload")
async def upload_document(request: Request, file: UploadFile = File(...),
                          regulation: str = Form(""), category: str = Form("")):
    """Upload a document (txt, md, pdf-text, csv) and ingest into the RAG knowledge base."""
    rag = request.app.state.rag_service

    # Read file content
    try:
        raw = await file.read()
        content = raw.decode("utf-8", errors="ignore")
    except Exception as e:
        logger.error("Failed to read uploaded file: %s", e)
        return {"status": "error", "message": f"Failed to read file: {e}"}

    if not content.strip():
        return {"status": "error", "message": "File is empty"}

    metadata = {}
    if regulation:
        metadata["regulation"] = regulation
    if category:
        metadata["category"] = category

    result = await rag.ingest_uploaded_document(file.filename, content, metadata)
    return result


@router.get("/stats")
async def rag_stats(request: Request):
    rag = request.app.state.rag_service
    stats = await rag.get_collection_stats()
    total_docs = sum(s.get("document_count", 0) for s in stats)
    return {
        "collections": len(stats),
        "total_documents": total_docs,
        "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
        "embedding_dim": 384,
    }
