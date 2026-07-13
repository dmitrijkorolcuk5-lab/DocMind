import type { Chat, ListResponse } from '../../entities/types'
import { apiRequest } from '../../shared/api/client'

export const getChats = () => apiRequest<ListResponse<Chat>>('/chats')

export const createChat = (title: string) =>
  apiRequest<Chat>('/chats', {
    method: 'POST',
    body: JSON.stringify({ title }),
  })

