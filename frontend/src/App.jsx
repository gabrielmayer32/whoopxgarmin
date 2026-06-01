import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import Dashboard from './pages/Dashboard'
import Recovery from './pages/Recovery'
import Training from './pages/Training'

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-bg">
        <Navbar />
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/recovery" element={<Recovery />} />
          <Route path="/training" element={<Training />} />
        </Routes>
      </div>
    </BrowserRouter>
  )
}
