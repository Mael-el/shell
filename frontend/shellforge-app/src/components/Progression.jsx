import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, ensureSession, resetSession } from '../session'

const Progression = () => {
  const [summary, setSummary] = useState(null)
  const [stats, setStats] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const sessionId = await ensureSession()
        const [summaryData, statsData, progressData] = await Promise.all([
          api(`/api/sessions/${sessionId}/summary`),
          api(`/api/sessions/${sessionId}/stats`),
          api(`/api/sessions/${sessionId}/progress`),
        ])
        if (cancelled) return
        setSummary(summaryData)
        setStats(statsData.stats)
        setHistory(progressData.progress)
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

  if (loading) return <main className="page"><p className="loader">Chargement de la progression…</p></main>
  if (error) return <main className="page"><div className="alert">{error}</div></main>

  const restart = () => {
    resetSession()
    window.location.href = '/'
  }

  return (
    <main className="page">
      <header className="page-head">
        <div>
          <p className="eyebrow">Tableau de bord</p>
          <h1>Ta progression</h1>
        </div>
        <button type="button" className="btn btn-ghost btn-small" onClick={restart}>
          Nouvelle session
        </button>
      </header>

      <section className="stat-row">
        <div className="stat-card"><strong>{summary.level}</strong><span>niveau</span></div>
        <div className="stat-card"><strong>{summary.xp_earned}</strong><span>XP / {summary.xp_total}</span></div>
        <div className="stat-card"><strong>{summary.completed_missions}/{summary.total_missions}</strong><span>missions</span></div>
        <div className="stat-card"><strong>{stats.success_rate}%</strong><span>réussite</span></div>
        <div className="stat-card"><strong>{stats.attempts}</strong><span>tentatives</span></div>
      </section>

      <section className="progress-levels">
        {summary.levels.map((level) => (
          <article key={level.id} className="progress-level" style={{ '--accent': level.accent }}>
            <header>
              <span className="level-icon" aria-hidden="true">{level.icon}</span>
              <div>
                <h2>{level.name}</h2>
                <small>{level.completed_missions}/{level.total_missions} missions · {level.xp_earned} XP</small>
              </div>
              <span className="badge">{level.percentage}%</span>
            </header>
            <div className="bar"><span style={{ width: `${level.percentage}%` }} /></div>
            <div className="progress-modules">
              {summary.modules
                .filter((module) => module.level === level.id)
                .map((module) => (
                  <Link key={module.id} to={`/module/${module.id}`} className="progress-module">
                    <span>{module.title}</span>
                    <span className="mini-bar"><i style={{ width: `${module.percentage}%` }} /></span>
                    <strong>{module.completed_missions}/{module.total_missions}</strong>
                  </Link>
                ))}
            </div>
          </article>
        ))}
      </section>

      <section className="history">
        <h2>Activité récente</h2>
        {history.length === 0 ? (
          <p className="empty">Aucune mission tentée pour l'instant.</p>
        ) : (
          <table className="table">
            <thead>
              <tr><th>Mission</th><th>Module</th><th>Tentatives</th><th>XP</th><th>Statut</th></tr>
            </thead>
            <tbody>
              {history.map((entry) => (
                <tr key={entry.mission_id}>
                  <td><Link to={`/mission/${entry.mission_id}`}>{entry.title}</Link></td>
                  <td>{entry.module_id}</td>
                  <td>{entry.attempts}</td>
                  <td>{entry.score}</td>
                  <td>{entry.correct ? <span className="pill ok">validée</span> : <span className="pill">en cours</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </main>
  )
}

export default Progression
