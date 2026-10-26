import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, ensureSession, withSession, difficultyLabel } from '../session'

const ModuleDetail = () => {
  const { moduleId } = useParams()
  const [module, setModule] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const sessionId = await ensureSession()
        const data = await api(withSession(`/api/modules/${moduleId}`, sessionId))
        if (!cancelled) setModule(data)
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
  }, [moduleId])

  if (loading) return <main className="page"><p className="loader">Chargement du module…</p></main>
  if (error) return <main className="page"><div className="alert">{error}</div></main>

  const nextMission = module.missions.find((mission) => !mission.completed) || module.missions[0]

  return (
    <main className="page">
      <nav className="crumbs">
        <Link to="/">Parcours</Link> <span>/</span>
        <Link to={`/niveau/${module.level}`}>Niveau {module.level}</Link> <span>/</span>
        <span>{module.id}</span>
      </nav>

      <header className="module-hero">
        <div>
          <p className="eyebrow">Niveau {module.level} · {module.level_name}</p>
          <h1>{module.title}</h1>
          <p>{module.description}</p>
        </div>
        <div className="level-hero-stats">
          <div><strong>{module.completed_missions}/{module.total_missions}</strong><span>missions</span></div>
          <div><strong>{module.earned_xp ?? 0}/{module.xp_reward}</strong><span>XP</span></div>
          <div><strong>{module.percentage}%</strong><span>achevé</span></div>
        </div>
      </header>

      <div className="bar"><span style={{ width: `${module.percentage}%` }} /></div>

      {nextMission && (
        <div className="resume-bar">
          <span>Prochaine étape : <strong>{nextMission.title}</strong></span>
          <Link to={`/mission/${nextMission.id}`} className="btn btn-primary btn-small">
            Ouvrir le laboratoire
          </Link>
        </div>
      )}

      <section className="mission-grid">
        {module.missions.map((mission, index) => (
          <article key={mission.id} className={`mission-card ${mission.completed ? 'done' : ''}`}>
            <header>
              <span className="mission-index">{mission.completed ? '✓' : index + 1}</span>
              <span className="badge badge-soft">{difficultyLabel[mission.difficulty] || mission.difficulty}</span>
            </header>
            <h2>{mission.title}</h2>
            <p>{mission.brief}</p>
            <ul className="objectives">
              {mission.objectives.slice(0, 3).map((objective) => (
                <li key={objective}>{objective}</li>
              ))}
            </ul>
            <div className="mission-card-meta">
              <span>{mission.points} XP</span>
              <span>{mission.check_count} preuves</span>
              <span>~{mission.estimated_minutes} min</span>
            </div>
            <Link to={`/mission/${mission.id}`} className="btn btn-ghost btn-small">
              {mission.completed ? 'Revoir la mission' : 'Commencer'}
            </Link>
          </article>
        ))}
      </section>
    </main>
  )
}

export default ModuleDetail
