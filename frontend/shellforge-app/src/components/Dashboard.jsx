import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, ensureSession, withSession } from '../session'

const Dashboard = () => {
  const [summary, setSummary] = useState(null)
  const [levels, setLevels] = useState([])
  const [nextMission, setNextMission] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const sessionId = await ensureSession()
        const [summaryData, levelsData] = await Promise.all([
          api(`/api/sessions/${sessionId}/summary`),
          api(withSession('/api/levels', sessionId)),
        ])
        if (cancelled) return
        setSummary(summaryData)
        setLevels(levelsData.levels)
        if (summaryData.next_mission) {
          const mission = await api(`/api/missions/${summaryData.next_mission}`)
          if (!cancelled) {
            setNextMission({ ...mission, moduleId: mission.module_id })
          }
        }
      } catch (err) {
        if (!cancelled) setError(err.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [])

  if (loading) return <main className="page"><p className="loader">Chargement du parcours…</p></main>
  if (error) return <main className="page"><div className="alert">{error}</div></main>

  const modulesByLevel = (levelId) =>
    (summary?.modules || []).filter((module) => module.level === levelId)

  return (
    <main className="page">
      <section className="hero">
        <div className="hero-copy">
          <p className="eyebrow">Terminal · Laboratoires · Preuves</p>
          <h1>
            Apprends une notion,
            <br />
            <span className="gradient-text">prouve-la dans le terminal.</span>
          </h1>
          <p className="hero-lead">
            15 modules, 30 missions vérifiées côté serveur : fondations Bash, administration Linux,
            reconnaissance, pentest et ingénierie de production. Chaque mission combine un cours, un
            laboratoire équipé et des contrôles qui valident tes preuves.
          </p>
          {nextMission && (
            <Link to={`/mission/${nextMission.id}`} className="btn btn-primary">
              {summary.completed_missions === 0 ? 'Commencer' : 'Reprendre'} : {nextMission.title}
            </Link>
          )}
        </div>
        <div className="hero-stats">
          <div className="stat">
            <span className="stat-value">{summary?.completed_missions ?? 0}</span>
            <span className="stat-label">missions validées</span>
          </div>
          <div className="stat">
            <span className="stat-value">{summary?.xp_earned ?? 0}</span>
            <span className="stat-label">XP gagnés</span>
          </div>
          <div className="stat">
            <span className="stat-value">N{summary?.level ?? 1}</span>
            <span className="stat-label">niveau</span>
          </div>
          <div className="stat stat-progress">
            <span className="stat-value">{summary?.overall_percentage ?? 0}%</span>
            <span className="stat-label">parcours</span>
            <div className="bar thin">
              <span style={{ width: `${summary?.overall_percentage ?? 0}%` }} />
            </div>
          </div>
        </div>
      </section>

      <section className="levels">
        {levels.map((level, index) => {
          const modules = modulesByLevel(level.id)
          return (
            <article
              key={level.id}
              className={`level-card ${level.unlocked ? '' : 'locked'}`}
              style={{ '--accent': level.accent }}
            >
              <div className="level-head">
                <span className="level-icon" aria-hidden="true">{level.icon}</span>
                <div>
                  <p className="eyebrow">Niveau {level.id}</p>
                  <h2>{level.name}</h2>
                  <p className="level-tagline">{level.tagline}</p>
                </div>
                <span className={`badge ${level.unlocked ? 'badge-open' : 'badge-locked'}`}>
                  {level.unlocked ? `${level.percentage}%` : 'verrouillé'}
                </span>
              </div>

              <p className="level-desc">{level.description}</p>

              <div className="bar">
                <span style={{ width: `${level.percentage}%` }} />
              </div>
              <div className="level-meta">
                <span>{level.completed_missions}/{level.total_missions} missions</span>
                <span>{level.xp_total} XP</span>
                {index > 0 && !level.unlocked && <span>Termine 70 % du niveau précédent</span>}
              </div>

              {level.unlocked ? (
                <div className="module-chips">
                  {modules.map((module) => (
                    <Link key={module.id} to={`/module/${module.id}`} className="chip">
                      <strong>{module.title}</strong>
                      <span>{module.completed_missions}/{module.total_missions}</span>
                    </Link>
                  ))}
                </div>
              ) : (
                <p className="lock-note">
                  Ce niveau s'ouvre automatiquement lorsque 70 % du niveau {level.id - 1} est validé —
                  tu peux néanmoins l'explorer dès maintenant.
                </p>
              )}

              <div className="level-actions">
                <Link to={`/niveau/${level.id}`} className="btn btn-ghost">
                  {level.unlocked ? 'Voir le niveau' : 'Explorer quand même'}
                </Link>
              </div>
            </article>
          )
        })}
      </section>
    </main>
  )
}

export default Dashboard
