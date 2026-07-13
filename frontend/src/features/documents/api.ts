import type { Document, ListResponse } from '../../entities/types'
import { apiRequest } from '../../shared/api/client'

export const getDocuments = () => apiRequest<ListResponse<Document>>('/documents')

