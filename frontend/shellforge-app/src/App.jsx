import { Route, Routes } from 'react-router-dom'
import './App.css'
import Navbar from './components/Navbar'
import Dashboard from './components/Dashboard'
import LevelDetail from './components/LevelDetail'
import ModuleDetail from './components/ModuleDetail'
import MissionDetail from './components/MissionDetail'
import Progression from './components/Progression'
import Dojo from './components/Dojo'

const NotFound = () => (
  <main className="page">
    <div className="empty-state">
      <p className="eyebrow">404</p>
      <h1>Cette page n'existe pas</h1>
      <p>Le laboratoire ne contient rien à cette adresse.</p>
    </div>
  </main>
)

const App = () => (
  <>
    <Navbar />
    <Routes>
      <Route path="/" element={<Dashboard />} />
      <Route path="/niveau/:levelId" element={<LevelDetail />} />
      <Route path="/module/:moduleId" element={<ModuleDetail />} />
      <Route path="/mission/:missionId" element={<MissionDetail />} />
      <Route path="/progression" element={<Progression />} />
      <Route path="/dojo" element={<Dojo />} />
      <Route path="*" element={<NotFound />} />
    </Routes>
  </>
)

export default App
