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

export interface ListResponse<T> {
  items: T[]
  total: number
}

