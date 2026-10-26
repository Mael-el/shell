import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, ensureSession, withSession, difficultyLabel } from '../session'

const LevelDetail = () => {
  const { levelId } = useParams()
  const [level, setLevel] = useState(null)
  const [modules, setModules] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const sessionId = await ensureSession()
        const [levelsData, modulesData] = await Promise.all([
          api(withSession('/api/levels', sessionId)),
          api(withSession('/api/modules', sessionId)),
        ])
        if (cancelled) return
        const found = levelsData.levels.find((item) => String(item.id) === String(levelId))
        if (!found) throw new Error('Niveau introuvable')
        setLevel(found)
        setModules(modulesData.modules.filter((module) => String(module.level) === String(levelId)))
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
  }, [levelId])

  if (loading) return <main className="page"><p className="loader">Chargement du niveau…</p></main>
  if (error) return <main className="page"><div className="alert">{error}</div></main>

  return (
    <main className="page" style={{ '--accent': level.accent }}>
      <nav className="crumbs">
        <Link to="/">Parcours</Link> <span>/</span> <span>Niveau {level.id}</span>
      </nav>

      <header className="level-hero">
        <span className="level-icon big" aria-hidden="true">{level.icon}</span>
        <div>
          <p className="eyebrow">Niveau {level.id}</p>
          <h1>{level.name}</h1>
          <p className="level-tagline">{level.tagline}</p>
        </div>
        <div className="level-hero-stats">
          <div><strong>{level.percentage}%</strong><span>achevé</span></div>
          <div><strong>{level.completed_missions}/{level.total_missions}</strong><span>missions</span></div>
          <div><strong>{level.xp_total}</strong><span>XP</span></div>
        </div>
      </header>

      <p className="level-desc">{level.description}</p>
      <div className="bar"><span style={{ width: `${level.percentage}%` }} /></div>

      {!level.unlocked && (
        <div className="alert alert-warn">
          Ce niveau est verrouillé : valide 70 % du niveau précédent pour l'ouvrir.
        </div>
      )}

      <section className="modules">
        {modules.map((module) => (
          <article key={module.id} className="module-card">
            <header className="module-head">
              <div>
                <h2>{module.title}</h2>
                <p>{module.description}</p>
              </div>
              <span className="badge">{module.completed_missions}/{module.total_missions}</span>
            </header>

            <ul className="mission-list">
              {module.missions.map((mission, index) => (
                <li key={mission.id} className={mission.completed ? 'done' : ''}>
                  <Link to={`/mission/${mission.id}`} className="mission-row">
                    <span className="mission-index">{mission.completed ? '✓' : index + 1}</span>
                    <span className="mission-info">
                      <strong>{mission.title}</strong>
                      <small>
                        {difficultyLabel[mission.difficulty] || mission.difficulty} · {mission.points} XP ·{' '}
                        {mission.check_count} preuves · ~{mission.estimated_minutes} min
                      </small>
                    </span>
                    <span className="mission-tags">
                      {mission.tags.slice(0, 2).map((tag) => (
                        <span key={tag} className="tag">{tag}</span>
                      ))}
                    </span>
                  </Link>
                </li>
              ))}
            </ul>

            <Link to={`/module/${module.id}`} className="btn btn-ghost btn-small">
              Détail du module
            </Link>
          </article>
        ))}
      </section>
    </main>
  )
}

export default LevelDetail
