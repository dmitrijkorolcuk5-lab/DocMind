export interface Document {
  id: string
  original_filename: string
  mime_type: string
  size_bytes: number
  status: 'uploaded' | 'processing' | 'ready' | 'failed' | 'deleting'
  error_message: string | null
  page_count: number | null
  chunk_count: number
  created_at: string
  updated_at: string
}

export interface Chat {
  id: string
  title: string
  created_at: string
  updated_at: string
}

export interface MessageSource {
  document_id: string
  filename: string
  page_start: number | null
  page_end: number | null
  excerpt: string
  score: number
}

export interface Message {
  id: string
  chat_id: string
  role: 'user' | 'assistant'
  content: string
  status: 'pending' | 'streaming' | 'completed' | 'failed'
  model: string | null
  created_at: string
  sources: MessageSource[]
}

export interface ListResponse<T> {
  items: T[]
  total: number
}
