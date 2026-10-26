import { useCallback, useEffect, useState } from 'react'
import { api, ensureSession } from '../session'

const ACCESS_LABEL = { gratuit: 'gratuit', freemium: 'freemium', payant: 'payant' }

const formatStars = (stars) => {
  if (typeof stars !== 'number') return null
  if (stars >= 1000) return `${(stars / 1000).toFixed(1).replace('.0', '').replace('.', ',')}k★`
  return `${stars}★`
}

const formatDate = (iso) => {
  if (!iso) return null
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return null
  return date.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' })
}

const Dojo = () => {
  const [sessionId, setSessionId] = useState(null)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const [pending, setPending] = useState(null)

  const load = useCallback(async (sid) => {
    const payload = await api(`/api/roadmap?session_id=${encodeURIComponent(sid)}`)
    setData(payload)
  }, [])

  useEffect(() => {
    let cancelled = false
    const boot = async () => {
      try {
        const sid = await ensureSession()
        if (cancelled) return
        setSessionId(sid)
        await load(sid)
      } catch (err) {
        if (!cancelled) setError(err.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    boot()
    return () => {
      cancelled = true
    }
  }, [load])

  const toggle = async (task) => {
    if (pending) return
    setPending(task.id)
    setError(null)
    try {
      const payload = await api('/api/roadmap/progress', {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId, task_id: task.id, done: !task.done }),
      })
      setData(payload)
    } catch (err) {
      setError(err.message)
    } finally {
      setPending(null)
    }
  }

  if (loading) return <main className="page"><p className="loader">Chargement du dojo…</p></main>
  if (error && !data) return <main className="page"><div className="alert">{error}</div></main>
  if (!data) return null

  const earned = data.badges.filter((badge) => badge.earned)
  const verification = data.verification

  return (
    <main className="page dojo-page">
      <header className="page-head dojo-head">
        <div>
          <p className="eyebrow">Plan d'entraînement · 12 semaines</p>
          <h1>{data.title}</h1>
          <p className="dojo-subtitle">{data.subtitle}</p>
        </div>
        <div className="dojo-score">
          <div>
            <strong>{data.completed_tasks}/{data.total_tasks}</strong>
            <span>tâches faites</span>
          </div>
          <div>
            <strong>{data.xp_earned}</strong>
            <span>XP comptés</span>
          </div>
          <div>
            <strong>{earned.length}/{data.badges.length}</strong>
            <span>badges</span>
          </div>
        </div>
      </header>

      <div className="dojo-progress">
        <div className="bar"><span style={{ width: `${data.percentage}%` }} /></div>
        <p className="muted">
          {data.percentage} % du plan · {data.xp_total} XP possibles ·{' '}
          {data.total_tasks - data.completed_tasks} tâches restantes
        </p>
      </div>

      {error && <div className="alert">{error}</div>}

      <section className="dojo-trio">
        <h2 className="dojo-section-title">Le trio pour commencer maintenant</h2>
        <div className="trio-grid">
          {data.resources.recommended.map((item) => (
            <a
              key={item.name}
              className="trio-card"
              href={item.url}
              target="_blank"
              rel="noreferrer"
            >
              <span className="tag">{item.domain}</span>
              <strong>{item.name}</strong>
              <span>{item.why}</span>
              <span className="trio-foot">
                <span className={`access-tag access-${item.access}`}>
                  {ACCESS_LABEL[item.access] || item.access}
                </span>
                {item.price && <span className="trio-price">{item.price}</span>}
                <span className="trio-link">ouvrir ↗</span>
              </span>
            </a>
          ))}
        </div>
      </section>

      <section className="dojo-levels">
        {data.levels.map((level, index) => (
          <article key={level.id} className="dojo-level" style={{ '--accent': level.accent }}>
            <header className="dojo-level-head">
              <span className="dojo-level-index">{String(index + 1).padStart(2, '0')}</span>
              <div>
                <h2>{level.name}</h2>
                <p className="muted">{level.weeks} · {level.goal}</p>
              </div>
              <div className="dojo-level-meta">
                <strong>{level.completed_tasks}/{level.total_tasks}</strong>
                <span>{level.xp_earned}/{level.xp_total} XP</span>
              </div>
            </header>

            <div className="bar thin"><span style={{ width: `${level.percentage}%` }} /></div>

            <ul className="task-list">
              {level.tasks.map((task) => (
                <li key={task.id} className={`task-row ${task.done ? 'done' : ''}`}>
                  <button
                    type="button"
                    className="task-check"
                    onClick={() => toggle(task)}
                    disabled={pending === task.id}
                    aria-pressed={task.done}
                    aria-label={`${task.done ? 'Décocher' : 'Cocher'} : ${task.label}`}
                  >
                    {task.done ? '✓' : '○'}
                  </button>
                  <div className="task-body">
                    <div className="task-title">
                      <strong>{task.label}</strong>
                      <span className="task-xp">+{task.xp} XP</span>
                    </div>
                    <p>{task.detail}</p>
                    {task.resource && (
                      <a
                        className="task-resource"
                        href={task.resource.url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        {task.resource.name} ↗
                      </a>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </article>
        ))}
      </section>

      <section className="dojo-badges">
        <h2 className="dojo-section-title">Badges</h2>
        <ul className="badge-grid">
          {data.badges.map((badge) => (
            <li key={badge.id} className={`badge-tile ${badge.earned ? 'earned' : ''}`}>
              <span className="badge-icon">{badge.icon}</span>
              <strong>{badge.label}</strong>
              <small>{badge.detail}</small>
            </li>
          ))}
        </ul>
      </section>

      <section className="dojo-method">
        <h2 className="dojo-section-title">Méthode : apprendre sans dépendre de l'IA</h2>
        <ol className="method-steps">
          {data.resources.method.map((step, index) => (
            <li key={`${index}-${step.step}`}>
              <span className="method-time">{step.step}</span>
              <span>{step.label}</span>
            </li>
          ))}
        </ol>
        <p className="muted dojo-principle">{data.principle}</p>
      </section>

      <section className="dojo-resources">
        <h2 className="dojo-section-title">Ressources</h2>
        <p className="alert alert-warn dojo-safety">{data.resources.safety}</p>
        {verification?.checked_at && (
          <p className="dojo-verified">
            <span className="verified-dot" aria-hidden="true" />
            Données vérifiées le {formatDate(verification.checked_at)} ·{' '}
            {verification.counts.github_checked} dépôts GitHub interrogés en direct (étoiles,
            licence, dernière mise à jour)
            {verification.counts.http_checked
              ? ` · ${verification.counts.http_reachable}/${verification.counts.resources} URL joignables`
              : ' · joignabilité HTTP non testée dans cet environnement'}
            .
          </p>
        )}

        <div className="resource-grid">
          {data.resources.categories.map((category) => (
            <article key={category.id} className="resource-card">
              <h3>{category.name}</h3>
              {category.intro && <p className="resource-intro">{category.intro}</p>}
              <ul>
                {category.items.map((item) => {
                  const meta = item.verified?.github
                  const dormant = meta && meta.archived
                  return (
                    <li key={`${category.id}-${item.name}`} className="resource-item">
                      <a href={item.url} target="_blank" rel="noreferrer" className="resource-link">
                        <span className="resource-name">
                          {item.name}
                          <span className={`access-tag access-${item.access}`}>
                            {ACCESS_LABEL[item.access] || item.access}
                          </span>
                          {dormant && <span className="access-tag access-dormant">archivé</span>}
                        </span>
                        <small>{item.note}</small>
                      </a>
                      <div className="resource-meta">
                        <span className="resource-provider">{item.provider}</span>
                        {meta && (
                          <span className="resource-stats">
                            {formatStars(meta.stars)}
                            {meta.license && meta.license !== 'NOASSERTION' ? ` · ${meta.license}` : ''}
                            {meta.pushed_at ? ` · maj ${formatDate(meta.pushed_at)}` : ''}
                          </span>
                        )}
                      </div>
                      {item.price && <p className="resource-price">{item.price}</p>}
                      {item.detail && <p className="resource-detail">{item.detail}</p>}
                    </li>
                  )
                })}
              </ul>
            </article>
          ))}
        </div>
      </section>
    </main>
  )
}

export default Dojo
