import { Route, Routes } from 'react-router-dom'
import './App.css'
import Navbar from './components/Navbar'
import Dashboard from './components/Dashboard'
import ModuleDetail from './components/ModuleDetail'
import ChallengeDetail from './components/ChallengeDetail'
import Profile from './components/Profile'

const App = () => {
  return (
    <>
      <Navbar />
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/module/:moduleId" element={<ModuleDetail />} />
        <Route path="/module/:moduleId/challenge/:challengeId" element={<ChallengeDetail />} />
        <Route
          path="/modules"
          element={
            <main className="page-shell">
              <div className="panel">
                <p className="eyebrow">Parcours</p>
                <h1>Modules Shell</h1>
                <p>Les modules arrivent bientôt dans une vue dédiée.</p>
              </div>
            </main>
          }
        />
        <Route path="/profile" element={<Profile />} />
      </Routes>
    </>
  )
}

export default App