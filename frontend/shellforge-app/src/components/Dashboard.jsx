import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiUrl } from '../config'

const Dashboard = () => {
  const [modules, setModules] = useState([])
  const [progress, setProgress] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [session, setSession] = useState(null)
  const [resumeChallenge, setResumeChallenge] = useState(null)

  useEffect(() => {
    const loadData = async () => {
      try {
        const modulesRes = await fetch(apiUrl('/api/modules'))
        if (!modulesRes.ok) throw new Error('Erreur chargement modules')
        const modulesData = await modulesRes.json()
        setModules(modulesData.modules)

        let sessionId = localStorage.getItem('shellforge_session_id')
        if (!sessionId) {
          const sessionRes = await fetch(apiUrl('/api/sessions'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: 'shellforge-user' })
          })
          if (!sessionRes.ok) throw new Error('Erreur session')
          const sessionData = await sessionRes.json()
          sessionId = sessionData.session_id
          localStorage.setItem('shellforge_session_id', sessionId)
        }

        setSession({ session_id: sessionId })

        const summaryRes = await fetch(apiUrl(`/api/sessions/${sessionId}/summary`))
        if (!summaryRes.ok) throw new Error('Erreur progression')
        const summaryData = await summaryRes.json()
        setProgress(summaryData.modules)
        setSession((current) => ({ ...(current || {}), ...summaryData }))
      } catch (err) {
        setError(err.message)
        console.error(err)
      } finally {
        setLoading(false)
      }
    }

    const storedResume = localStorage.getItem('shellforge_last_challenge')
    if (storedResume) {
      try {
        setResumeChallenge(JSON.parse(storedResume))
      } catch (err) {
        localStorage.removeItem('shellforge_last_challenge')
      }
    }

    loadData()
  }, [])

  if (loading) {
    return <div className="dashboard-loading">Chargement de SHELLFORGE...</div>
  }

  if (error) {
    return <div className="dashboard-error">{error}</div>
  }

  const moduleStats = modules.map((module) => {
    const moduleProgress = progress.find((item) => item.id === module.id) || {
      total_challenges: 0,
      completed_challenges: 0,
      percentage: 0,
      earned_xp: 0,
    }

    return {
      ...module,
      totalChallenges: moduleProgress.total_challenges,
      completed: moduleProgress.completed_challenges,
      percentage: moduleProgress.percentage,
      earnedXP: moduleProgress.earned_xp,
      unlocked: moduleProgress.unlocked ?? true,
    }
  })

  const totalXP = moduleStats.reduce((sum, m) => sum + m.earnedXP, 0)
  const totalCompletedChallenges = session?.completed_challenges ?? 0
  const totalChallenges = session?.total_challenges ?? 0
  const overallCompletion = session?.overall_percentage ?? (
    moduleStats.length > 0
      ? (moduleStats.reduce((sum, m) => sum + Number(m.percentage), 0) / moduleStats.length).toFixed(1)
      : 0
  )

  return (
    <main className="dashboard-container">
      <header className="header-wrapper">
        <div>
          <p className="eyebrow">Bienvenue</p>
          <h1>
            <span className="icon">🐚</span> SHELLFORGE
          </h1>
        </div>
        <p className="subtitle">Plateforme interactive d'apprentissage Bash</p>
      </header>

      {resumeChallenge && (
        <section className="resume-banner">
          <div>
            <p className="eyebrow">Reprise</p>
            <h3>Continuer : {resumeChallenge.title}</h3>
          </div>
          <Link to={resumeChallenge.path} className="module-link">Reprendre</Link>
        </section>
      )}

      <section className="stats-grid">
        <div className="stat-card">
          <div className="stat-number">{modules.length}</div>
          <div className="stat-label">Modules</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{totalXP} XP</div>
          <div className="stat-label">Total XP</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{overallCompletion}%</div>
          <div className="stat-label">Progression</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{totalCompletedChallenges}/{totalChallenges}</div>
          <div className="stat-label">Défis validés</div>
        </div>
      </section>

      <section className="modules-section">
        <div className="section-title-row">
          <h2>Parcours d'apprentissage</h2>
          <span>7 niveaux</span>
        </div>

        <div className="modules-grid">
          {moduleStats.map((module) => (
            <div
              key={module.id}
              className={`module-card level-${module.level} ${module.percentage === 100 ? 'completed' : ''} ${!module.unlocked ? 'locked' : ''}`}
            >
              <div className="module-header">
                <span className="level-badge">Niveau {module.level}</span>
                <h3>{module.title}</h3>
              </div>
              <p className="module-desc">{module.description}</p>

              {!module.unlocked ? (
                <div className="module-lock-message">
                  Termine le module précédent pour débloquer ce parcours.
                </div>
              ) : (
                <>
                  <div className="progress-bar">
                    <div className="progress-fill" style={{ width: `${module.percentage}%` }} />
                  </div>

                  <div className="module-meta">
                    <span className="progress-text">{module.percentage}%</span>
                    <span className="xp-text">{module.xp_reward || 0} XP</span>
                  </div>
                </>
              )}

              <Link
                to={module.unlocked ? `/module/${module.id}` : '#'}
                className={`module-link ${module.percentage === 100 ? 'completed' : ''} ${!module.unlocked ? 'locked-link' : ''}`}
                onClick={(event) => {
                  if (!module.unlocked) {
                    event.preventDefault()
                  }
                }}
              >
                {module.unlocked ? `Voir les défis (${module.totalChallenges})` : 'Verrouillé'}
              </Link>
            </div>
          ))}
        </div>
      </section>

      {error && <p className="error-message">{error}</p>}
    </main>
  )
}

export default Dashboard