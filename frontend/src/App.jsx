import { Routes, Route } from 'react-router-dom'
import AppLayout from './layouts/AppLayout'
import HomePage from './pages/HomePage'
import CompoundsPage from './pages/CompoundsPage'
import CompoundDetailPage from './pages/CompoundDetailPage'
import ArticlesPage from './pages/ArticlesPage'
import TargetsPage from './pages/TargetsPage'
import SearchPage from './pages/SearchPage'

export default function App() {
  return (
    <Routes>
      <Route element={<AppLayout />}>
        <Route path="/" element={<HomePage />} />
        <Route path="/compounds" element={<CompoundsPage />} />
        <Route path="/compounds/:chemblId" element={<CompoundDetailPage />} />
        <Route path="/articles" element={<ArticlesPage />} />
        <Route path="/targets" element={<TargetsPage />} />
        <Route path="/search" element={<SearchPage />} />
      </Route>
    </Routes>
  )
}
