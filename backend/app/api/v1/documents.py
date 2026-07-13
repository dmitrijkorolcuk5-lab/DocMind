from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.dependencies import get_document_service
from app.documents.schemas import DocumentList
from app.documents.service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])
DocumentServiceDependency = Annotated[DocumentService, Depends(get_document_service)]


@router.get("", response_model=DocumentList)
async def list_documents(
    service: DocumentServiceDependency,
) -> DocumentList:
    return await service.list_documents()
