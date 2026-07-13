import type { Chat, Document, ListResponse, Message } from '../../entities/types'
import { apiRequest, streamRequest } from '../../shared/api/client'

export const getChats = () => apiRequest<ListResponse<Chat>>('/chats')

export const createChat = (title: string) =>
  apiRequest<Chat>('/chats', {
    method: 'POST',
    body: JSON.stringify({ title }),
  })

export const getChatDocuments = (chatId: string) =>
  apiRequest<ListResponse<Document>>(`/chats/${chatId}/documents`)

export const updateChatDocuments = (chatId: string, documentIds: string[]) =>
  apiRequest<ListResponse<Document>>(`/chats/${chatId}/documents`, {
    method: 'PUT',
    body: JSON.stringify({ document_ids: documentIds }),
  })

export const getMessages = (chatId: string) =>
  apiRequest<ListResponse<Message>>(`/chats/${chatId}/messages`)

export const streamChatMessage = (
  chatId: string,
  content: string,
  onEvent: (event: string, data: unknown) => void,
) => streamRequest(`/chats/${chatId}/messages/stream`, { content }, onEvent)
