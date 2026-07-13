from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile, status

from app.api.dependencies import get_document_service
from app.documents.schemas import DocumentList, DocumentRead
from app.documents.service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])
DocumentServiceDependency = Annotated[DocumentService, Depends(get_document_service)]


@router.get("", response_model=DocumentList)
async def list_documents(
    service: DocumentServiceDependency,
) -> DocumentList:
    return await service.list_documents()


@router.post("", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    service: DocumentServiceDependency,
    file: Annotated[UploadFile, File()],
) -> DocumentRead:
    data = await file.read()
    return await service.upload_document(
        original_filename=file.filename or "document",
        mime_type=file.content_type or "application/octet-stream",
        data=data,
    )


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: UUID,
    service: DocumentServiceDependency,
) -> DocumentRead:
    return await service.get_document(document_id)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    service: DocumentServiceDependency,
) -> None:
    await service.delete_document(document_id)
