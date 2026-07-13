from app.documents.repository import DocumentRepository
from app.documents.schemas import DocumentList, DocumentRead


class DocumentService:
    def __init__(self, repository: DocumentRepository) -> None:
        self._repository = repository

    async def list_documents(self) -> DocumentList:
        documents, total = await self._repository.list()
        return DocumentList(
            items=[DocumentRead.model_validate(document) for document in documents], total=total
        )

