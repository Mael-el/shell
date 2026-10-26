import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiUrl } from '../config'

const Profile = () => {
  const [summary, setSummary] = useState(null)
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const loadProfile = async () => {
      try {
        const sessionId = localStorage.getItem('shellforge_session_id')
        if (!sessionId) {
          throw new Error('Aucune session active trouvée')
        }

        const summaryRes = await fetch(apiUrl(`/api/sessions/${sessionId}/summary`))
        if (!summaryRes.ok) throw new Error('Impossible de charger le profil')
        const summaryData = await summaryRes.json()
        setSummary(summaryData)

        const statsRes = await fetch(apiUrl(`/api/sessions/${sessionId}/stats`))
        if (statsRes.ok) {
          const statsData = await statsRes.json()
          setStats(statsData.stats)
        }
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    loadProfile()
  }, [])

  if (loading) {
    return <main className="page-shell"><div className="panel"><p className="eyebrow">Profil</p><h1>Chargement...</h1></div></main>
  }

  if (error) {
    return (
      <main className="page-shell">
        <div className="panel">
          <p className="eyebrow">Erreur</p>
          <h1>{error}</h1>
          <Link to="/" className="module-link">Retour à l'accueil</Link>
        </div>
      </main>
    )
  }

  return (
    <main className="dashboard-container">
      <header className="header-wrapper">
        <div>
          <p className="eyebrow">Profil apprenant</p>
          <h1>Niveau {summary.level}</h1>
        </div>
        <p className="subtitle">Progression, XP et maîtrise du shell</p>
      </header>

      <section className="stats-grid">
        <div className="stat-card">
          <div className="stat-number">{summary.xp_earned || 0}</div>
          <div className="stat-label">XP accumulés</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{summary.overall_percentage || 0}%</div>
          <div className="stat-label">Progression globale</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{summary.completed_challenges || 0}</div>
          <div className="stat-label">Défis validés</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{stats?.correct ?? 0}</div>
          <div className="stat-label">Réussites</div>
        </div>
      </section>

      <section className="modules-section">
        <div className="section-title-row">
          <h2>Progression par module</h2>
          <Link to="/" className="module-link">Retour</Link>
        </div>

        <div className="modules-grid">
          {summary.modules.map((module) => (
            <div key={module.id} className="module-card">
              <div className="module-header">
                <span className="level-badge">Niveau {module.level}</span>
                <h3>{module.title}</h3>
              </div>

              <p className="module-desc">{module.completed_challenges}/{module.total_challenges} missions complètes</p>

              <div className="progress-bar">
                <div className="progress-fill" style={{ width: `${module.percentage}%` }} />
              </div>

              <div className="module-meta">
                <span>{module.percentage}%</span>
                <span>{module.earned_xp || 0} XP</span>
              </div>

              <Link to={`/module/${module.id}`} className="module-link">
                Ouvrir le module
              </Link>
            </div>
          ))}
        </div>
      </section>
    </main>
  )
}

export default Profile
