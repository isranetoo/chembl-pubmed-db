import { Routes, Route } from 'react-router-dom'
import AppLayout from './layouts/AppLayout'
import HomePage from './pages/HomePage'
import CompoundsPage from './pages/CompoundsPage'
import CompoundDetailPage from './pages/CompoundDetailPage'
import ArticlesPage from './pages/ArticlesPage'
import TargetsPage from './pages/TargetsPage'
import TargetDetailPage from './pages/TargetDetailPage'
import SearchPage from './pages/SearchPage'
import ComparePage from './pages/ComparePage'
import AnalyticsPage from './pages/AnalyticsPage'
import ToolsPage from './pages/ToolsPage'
import HistopathologyPage from './pages/HistopathologyPage'
import HistopathologyCohortPage from './pages/HistopathologyCohortPage'
import TrialsPage from './pages/TrialsPage'

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/compounds" element={<CompoundsPage />} />
        <Route path="/compounds/:chemblId" element={<CompoundDetailPage />} />
        <Route path="/compare" element={<ComparePage />} />
        <Route path="/analytics" element={<AnalyticsPage />} />
        <Route path="/tools" element={<ToolsPage />} />
        <Route path="/histopathology" element={<HistopathologyPage />} />
        <Route path="/histopathology/:cohort" element={<HistopathologyCohortPage />} />
        <Route path="/trials" element={<TrialsPage />} />
        <Route path="/articles" element={<ArticlesPage />} />
        <Route path="/targets" element={<TargetsPage />} />
        <Route path="/targets/:chemblId" element={<TargetDetailPage />} />
        <Route path="/search" element={<SearchPage />} />
      </Route>
    </Routes>
  )
}
