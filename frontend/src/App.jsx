import { Routes, Route, Navigate } from 'react-router-dom'
import Navbar from './components/Navbar.jsx'
import BookingPage from './components/BookingPage.jsx'
import MeetingList from './components/MeetingList.jsx'
import NotesUpload from './components/NotesUpload.jsx'
import ActionItemTracker from './components/ActionItemTracker.jsx'
import Dashboard from './components/Dashboard.jsx'

export default function App() {
  return (
    <div className="main-layout">
      <Navbar />
      <main className="page-content animate-in">
        <Routes>
          <Route path="/"           element={<Dashboard />} />
          <Route path="/book"       element={<BookingPage />} />
          <Route path="/meetings"   element={<MeetingList />} />
          <Route path="/notes"      element={<NotesUpload />} />
          <Route path="/actions"    element={<ActionItemTracker />} />
          <Route path="*"           element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  )
}
