import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import Upload from './pages/Upload'
import Preview from './pages/Preview'
import AuditLogs from './pages/AuditLogs'
import './App.css'

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        <Navbar />
        <main className="pt-16">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <Routes>
              <Route path="/" element={<Upload />} />
              <Route path="/preview" element={<Preview />} />
              <Route path="/audit-logs" element={<AuditLogs />} />
            </Routes>
          </div>
        </main>
      </div>
    </Router>
  )
}

export default App
