import { Navigate, Route, Routes } from 'react-router-dom'

import { ChatDetailsPage } from '../pages/ChatDetailsPage'
import { ChatsPage } from '../pages/ChatsPage'
import { DocumentsPage } from '../pages/DocumentsPage'
import { AppLayout } from './AppLayout'

export function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route index element={<Navigate to="/documents" replace />} />
        <Route path="documents" element={<DocumentsPage />} />
        <Route path="chats" element={<ChatsPage />} />
        <Route path="chats/:chatId" element={<ChatDetailsPage />} />
        <Route path="*" element={<Navigate to="/documents" replace />} />
      </Route>
    </Routes>
  )
}

