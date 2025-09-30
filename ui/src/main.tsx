import { createRoot } from 'react-dom/client'
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import './index.css'
import { HomePage } from './pages/HomePage.tsx'
import DashboardPage from './pages/DashboardPage.tsx'
import { ResultsPage } from './components/ResultsPage.tsx'

createRoot(document.getElementById('root')!).render(
  <Router>
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/dashboard" element={<DashboardPage />} />
      <Route path="/results/:id" element={<ResultsPage />} />
    </Routes>
  </Router>
)
