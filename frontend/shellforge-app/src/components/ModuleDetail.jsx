import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiUrl } from '../config'

const ModuleDetail = () => {
  const { moduleId } = useParams()
  const [module, setModule] = useState(null)
  const [challenges, setChallenges] = useState([])
  const [completedChallenges, setCompletedChallenges] = useState([])
  const [moduleUnlocked, setModuleUnlocked] = useState(true)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const loadModule = async () => {
      try {
        setLoading(true)
        setError(null)

        const modulesRes = await fetch(apiUrl('/api/modules'))
        if (!modulesRes.ok) throw new Error('Impossible de charger le module')
        const modulesData = await modulesRes.json()
        const foundModule = modulesData.modules.find((item) => item.id === moduleId)

        if (!foundModule) {
          throw new Error('Module introuvable')
        }

        setModule(foundModule)

        const challengesRes = await fetch(apiUrl(`/api/modules/${moduleId}/challenges`))
        if (!challengesRes.ok) throw new Error('Impossible de charger les missions')
        const challengesData = await challengesRes.json()
        setChallenges(challengesData.challenges)

        const sessionId = localStorage.getItem('shellforge_session_id')
        if (sessionId) {
          const summaryRes = await fetch(apiUrl(`/api/sessions/${sessionId}/summary`))
          if (summaryRes.ok) {
            const summaryData = await summaryRes.json()
            const moduleSummary = summaryData.modules.find((item) => item.id === moduleId)
            if (moduleSummary) {
              setModuleUnlocked(moduleSummary.unlocked ?? true)
            }

            const progressRes = await fetch(apiUrl(`/api/sessions/${sessionId}/progress`))
            if (progressRes.ok) {
              const progressData = await progressRes.json()
              const completedIds = progressData.progress
                .filter((entry) => entry.correct)
                .map((entry) => entry.challenge_id)
              setCompletedChallenges(completedIds)
            }
          }
        }
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    loadModule()
  }, [moduleId])

  if (loading) {
    return <div className="dashboard-loading">Chargement du module...</div>
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
          <p className="eyebrow">Module</p>
          <h1>{module.title}</h1>
        </div>
        <p className="subtitle">{module.description}</p>
      </header>

      <section className="stats-grid">
        <div className="stat-card">
          <div className="stat-number">{module.level}</div>
          <div className="stat-label">Niveau</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{module.xp_reward} XP</div>
          <div className="stat-label">Récompense</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{module.difficulty}</div>
          <div className="stat-label">Difficulté</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{challenges.length}</div>
          <div className="stat-label">Missions</div>
        </div>
      </section>

      <section className="modules-section">
        <div className="section-title-row">
          <h2>Missions du module</h2>
          <Link to="/" className="module-link">← Retour</Link>
        </div>

        {!moduleUnlocked && (
          <div className="module-lock-message" style={{ marginBottom: '1rem' }}>
            Ce module est verrouillé tant que le module précédent n’est pas terminé.
          </div>
        )}

        <div className="modules-grid">
          {challenges.map((challenge) => (
            <article key={challenge.id} className="module-card">
              <div className="module-header">
                <span className="level-badge">{challenge.difficulty}</span>
                <h3>{challenge.title}</h3>
              </div>

              <p className="module-desc">{challenge.description}</p>

              <div className="challenge-box">
                <span className="challenge-label">Commande</span>
                <pre>{challenge.command}</pre>
              </div>

              <div className="module-meta">
                <span>{challenge.points} points</span>
                <span>{challenge.validation}</span>
              </div>

              <Link
                to={moduleUnlocked ? `/module/${module.id}/challenge/${challenge.id}` : '#'}
                className={`module-link ${!moduleUnlocked ? 'locked-link' : ''}`}
                onClick={(event) => {
                  if (!moduleUnlocked) {
                    event.preventDefault()
                  }
                }}
              >
                {completedChallenges.includes(challenge.id) ? 'Reprendre la mission' : 'Commencer la mission'}
              </Link>
            </article>
          ))}
        </div>
      </section>
    </main>
  )
}

export default ModuleDetail
