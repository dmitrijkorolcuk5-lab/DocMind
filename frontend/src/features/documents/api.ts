import type { Document, ListResponse } from '../../entities/types'
import { apiRequest } from '../../shared/api/client'

export const getDocuments = () => apiRequest<ListResponse<Document>>('/documents')

export const uploadDocument = (file: File) => {
  const formData = new FormData()
  formData.append('file', file)
  return apiRequest<Document>('/documents', { method: 'POST', body: formData })
}

export const deleteDocument = (documentId: string) =>
  apiRequest<void>(`/documents/${documentId}`, { method: 'DELETE' })
