import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import Console from './Console'
import { api, difficultyLabel, ensureSession } from '../session'

const TABS = [
  { id: 'cours', label: 'Cours' },
  { id: 'labo', label: 'Laboratoire' },
  { id: 'fichiers', label: 'Fichiers' },
]

const MissionDetail = () => {
  const { missionId } = useParams()
  const [sessionId, setSessionId] = useState(null)
  const [mission, setMission] = useState(null)
  const [learning, setLearning] = useState({ total_sections: 0, completed_sections: 0, progress_percent: 0, sections: [] })
  const [progress, setProgress] = useState({ attempts: 0, completed: false, score: 0 })
  const [files, setFiles] = useState([])
  const [selectedFile, setSelectedFile] = useState(null)
  const [tab, setTab] = useState('cours')
  const [hintLevel, setHintLevel] = useState(0)
  const [verification, setVerification] = useState(null)
  const [verifying, setVerifying] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const loadFiles = useCallback(
    async (sid) => {
      if (!sid) return
      const data = await api(
        `/api/labs/files?session_id=${encodeURIComponent(sid)}&working_dir=${encodeURIComponent(missionId)}`,
      )
      setFiles(data.entries)
    },
    [missionId],
  )

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        const sid = await ensureSession()
        if (cancelled) return
        setSessionId(sid)
        const data = await api(
          `/api/missions/${missionId}?session_id=${encodeURIComponent(sid)}`,
        )
        if (cancelled) return
        setMission(data)
        setLearning(data.learning_progress)
        setProgress(data.progress)
        await loadFiles(sid)
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
  }, [missionId, loadFiles])

  const checksById = useMemo(() => {
    const map = {}
    for (const check of verification?.checks || []) map[check.id] = check
    return map
  }, [verification])

  const toggleSection = async (sectionId, status) => {
    try {
      const data = await api('/api/learning/progress', {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId, mission_id: missionId, section_id: sectionId, status }),
      })
      setLearning(data)
    } catch (err) {
      setError(err.message)
    }
  }

  const verify = async () => {
    if (verifying) return
    setVerifying(true)
    setError(null)
    try {
      const data = await api(`/api/missions/${missionId}/verify`, {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId }),
      })
      setVerification(data)
      setProgress({
        attempts: progress.attempts + 1,
        completed: progress.completed || data.passed,
        score: progress.score + (data.score_awarded || 0),
      })
      await loadFiles(sessionId)
      if (data.passed) setTab('labo')
    } catch (err) {
      setError(err.message)
    } finally {
      setVerifying(false)
    }
  }

  const resetLab = async () => {
    try {
      await api('/api/labs/reset', {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId, mission_id: missionId }),
      })
      setVerification(null)
      setSelectedFile(null)
      await loadFiles(sessionId)
    } catch (err) {
      setError(err.message)
    }
  }

  if (loading) return <main className="page"><p className="loader">Préparation du laboratoire…</p></main>
  if (error && !mission) return <main className="page"><div className="alert">{error}</div></main>

  const passedCount = verification?.checks?.filter((check) => check.passed).length ?? 0

  return (
    <main className="page mission-page">
      <nav className="crumbs">
        <Link to="/">Parcours</Link> <span>/</span>
        <Link to={`/niveau/${mission.level}`}>Niveau {mission.level}</Link> <span>/</span>
        <Link to={`/module/${mission.module_id}`}>{mission.module_title}</Link>
      </nav>

      <header className="mission-hero">
        <div>
          <p className="eyebrow">
            Mission {mission.id} · {mission.module_title}
          </p>
          <h1>{mission.title}</h1>
          <p className="mission-brief">{mission.brief}</p>
        </div>
        <div className="mission-meta">
          <span className="badge badge-accent">{difficultyLabel[mission.difficulty] || mission.difficulty}</span>
          <span className="badge">{mission.points} XP</span>
          <span className="badge">{mission.lab.checks.length} preuves</span>
          <span className="badge">~{mission.estimated_minutes} min</span>
          {progress.completed && <span className="badge badge-open">validée</span>}
        </div>
      </header>

      <div className="tabs">
        {TABS.map((item) => (
          <button
            key={item.id}
            type="button"
            className={`tab ${tab === item.id ? 'active' : ''}`}
            onClick={() => setTab(item.id)}
          >
            {item.label}
          </button>
        ))}
        <span className="tabs-spacer" />
        <span className="tabs-note">
          {verification
            ? `${passedCount}/${verification.total_count} preuves validées`
            : `${progress.attempts} tentative${progress.attempts > 1 ? 's' : ''}`}
        </span>
      </div>

      <div className="mission-layout">
        <div className="mission-main">
          {tab === 'cours' && (
            <section className="panel">
              <div className="panel-head">
                <h2>Le cours</h2>
                <span className="muted">
                  {learning.completed_sections}/{learning.total_sections} sections lues
                </span>
              </div>
              <div className="bar thin"><span style={{ width: `${learning.progress_percent}%` }} /></div>
              <p className="lesson-summary">{mission.lesson.summary}</p>

              <div className="sections">
                {mission.lesson.sections.map((section, index) => {
                  const state = learning.sections.find((item) => item.id === section.id)
                  const done = state?.status === 'completed'
                  return (
                    <article key={section.id} className={`section-card ${done ? 'done' : ''}`}>
                      <header>
                        <span className="section-index">{String(index + 1).padStart(2, '0')}</span>
                        <h3>{section.name}</h3>
                        <button
                          type="button"
                          className={`btn btn-small ${done ? 'btn-ghost' : 'btn-primary'}`}
                          onClick={() => toggleSection(section.id, done ? 'in_progress' : 'completed')}
                        >
                          {done ? 'Lu ✓' : 'Marquer comme lu'}
                        </button>
                      </header>
                      <p>{section.content}</p>
                    </article>
                  )
                })}
              </div>

              {mission.lesson.references?.length > 0 && (
                <div className="references">
                  <h3>Références de commandes</h3>
                  <table className="table">
                    <thead>
                      <tr><th>Commande</th><th>Rôle</th><th>Exemple</th></tr>
                    </thead>
                    <tbody>
                      {mission.lesson.references.map((reference) => (
                        <tr key={reference.command}>
                          <td><code>{reference.command}</code></td>
                          <td>{reference.role}</td>
                          <td><code>{reference.example}</code></td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {mission.lesson.pitfalls?.length > 0 && (
                <div className="callout callout-warn">
                  <h3>Pièges à éviter</h3>
                  <ul>
                    {mission.lesson.pitfalls.map((pitfall) => <li key={pitfall}>{pitfall}</li>)}
                  </ul>
                </div>
              )}

              {mission.remediation && (
                <div className="callout">
                  <h3>Vision défensive / ingénierie</h3>
                  <p>{mission.remediation}</p>
                </div>
              )}
            </section>
          )}

          {tab === 'labo' && (
            <>
              <section className="panel">
                <div className="panel-head">
                  <h2>Le laboratoire</h2>
                  <button type="button" className="link-btn" onClick={resetLab}>
                    réinitialiser l'espace
                  </button>
                </div>
                <p className="lab-task">{mission.lab.task}</p>

                {mission.lab.steps?.length > 0 && (
                  <ol className="steps">
                    {mission.lab.steps.map((step) => <li key={step}>{step}</li>)}
                  </ol>
                )}

                {mission.lab.files?.length > 0 && (
                  <div className="starter-files">
                    <h3>Fichiers fournis</h3>
                    <div className="file-tags">
                      {mission.lab.files.map((file) => (
                        <button
                          key={file}
                          type="button"
                          className="tag tag-button"
                          onClick={() => {
                            setSelectedFile(files.find((entry) => entry.path === file) || null)
                            setTab('fichiers')
                          }}
                        >
                          {file}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {mission.lab.hints?.length > 0 && (
                  <div className="hints">
                    <div className="hints-head">
                      <h3>Indices</h3>
                      <button
                        type="button"
                        className="btn btn-ghost btn-small"
                        onClick={() => setHintLevel((current) => Math.min(current + 1, mission.lab.hints.length))}
                        disabled={hintLevel >= mission.lab.hints.length}
                      >
                        {hintLevel === 0 ? 'Afficher un indice' : 'Indice suivant'}
                      </button>
                    </div>
                    {mission.lab.hints.slice(0, hintLevel).map((hint, index) => (
                      <p key={hint} className="hint">
                        <strong>#{index + 1}</strong> {hint}
                      </p>
                    ))}
                    {hintLevel === 0 && <p className="muted">Essaie d'abord par toi-même : les indices sont progressifs.</p>}
                  </div>
                )}
              </section>

              <section className="panel">
                <div className="panel-head">
                  <h2>Console</h2>
                  <span className="muted">session {sessionId?.slice(0, 8)}</span>
                </div>
                {sessionId && (
                  <Console sessionId={sessionId} missionId={missionId} onAfterRun={() => loadFiles(sessionId)} />
                )}
              </section>

              <section className="panel verify-panel">
                <div className="panel-head">
                  <h2>Vérification des preuves</h2>
                  <button type="button" className="btn btn-primary" onClick={verify} disabled={verifying}>
                    {verifying ? 'Vérification…' : 'Vérifier mes preuves'}
                  </button>
                </div>
                <p className="muted">
                  {mission.lab.verify_hint || 'Le serveur exécute les contrôles dans ton espace de travail. Aucun fichier ne sort du laboratoire.'}
                </p>

                <ul className="checks">
                  {mission.lab.checks.map((check) => {
                    const result = checksById[check.id]
                    const status = result ? (result.passed ? 'pass' : 'fail') : 'pending'
                    return (
                      <li key={check.id} className={`check ${status}`}>
                        <span className="check-icon">{status === 'pass' ? '✓' : status === 'fail' ? '✕' : '○'}</span>
                        <div>
                          <strong>{check.label}</strong>
                          {result?.detail && <small>{result.detail}</small>}
                        </div>
                      </li>
                    )
                  })}
                </ul>

                {verification && (
                  <div className={`verdict ${verification.passed ? 'ok' : 'ko'}`}>
                    <strong>
                      {verification.passed
                        ? `Mission validée · +${verification.score_awarded} XP`
                        : `${verification.passed_count}/${verification.total_count} preuves — continue`}
                    </strong>
                    <span>{verification.message}</span>
                  </div>
                )}

                {verification?.passed && verification.solution && (
                  <details className="solution">
                    <summary>Voir la solution de référence</summary>
                    <pre>{verification.solution}</pre>
                  </details>
                )}

                {verification?.passed && verification.next_mission && (
                  <Link to={`/mission/${verification.next_mission}`} className="btn btn-primary">
                    Mission suivante →
                  </Link>
                )}
              </section>
            </>
          )}

          {tab === 'fichiers' && (
            <section className="panel files-panel">
              <div className="panel-head">
                <h2>Espace de travail</h2>
                <button type="button" className="link-btn" onClick={() => loadFiles(sessionId)}>
                  actualiser
                </button>
              </div>
              <div className="files-layout">
                <ul className="file-list">
                  {files.map((entry) => (
                    <li key={entry.path}>
                      {entry.type === 'directory' ? (
                        <div className="file-row directory">
                          <span className="file-icon">▸</span>
                          <code>{entry.path}</code>
                        </div>
                      ) : (
                        <button
                          type="button"
                          className={`file-row ${selectedFile?.path === entry.path ? 'active' : ''}`}
                          onClick={() => setSelectedFile(entry)}
                        >
                          <span className="file-icon">·</span>
                          <code>{entry.path}</code>
                          <small>{entry.size} o</small>
                        </button>
                      )}
                    </li>
                  ))}
                </ul>
                <div className="file-preview">
                  {selectedFile ? (
                    <>
                      <div className="file-preview-head">
                        <strong>{selectedFile.path}</strong>
                        <span className="muted">{selectedFile.size} octets</span>
                      </div>
                      <pre>{selectedFile.content ?? 'Aperçu indisponible (fichier trop volumineux).'}</pre>
                    </>
                  ) : (
                    <p className="muted">Sélectionne un fichier pour l'inspecter. Tu peux aussi le lire dans la console.</p>
                  )}
                </div>
              </div>
            </section>
          )}

          {error && <div className="alert">{error}</div>}
        </div>

        <aside className="mission-side">
          <div className="side-card">
            <h3>Objectifs</h3>
            <ul className="objectives">
              {mission.objectives.map((objective) => <li key={objective}>{objective}</li>)}
            </ul>
          </div>

          <div className="side-card">
            <h3>État</h3>
            <dl className="kv">
              <div><dt>Tentatives</dt><dd>{progress.attempts}</dd></div>
              <div><dt>XP mission</dt><dd>{mission.points}</dd></div>
              <div><dt>XP gagnés</dt><dd>{progress.score}</dd></div>
              <div><dt>Preuves</dt><dd>{verification ? `${passedCount}/${verification.total_count}` : `${mission.lab.checks.length}`}</dd></div>
            </dl>
            <button type="button" className="btn btn-primary btn-block" onClick={verify} disabled={verifying}>
              {verifying ? 'Vérification…' : 'Vérifier mes preuves'}
            </button>
          </div>

          {mission.tags?.length > 0 && (
            <div className="side-card">
              <h3>Compétences</h3>
              <div className="file-tags">
                {mission.tags.map((tag) => <span key={tag} className="tag">{tag}</span>)}
              </div>
            </div>
          )}

          <div className="side-card side-note">
            <h3>Bonne pratique</h3>
            <p>
              Le laboratoire est isolé par session : tu peux tout casser et réinitialiser. Prends l'habitude de
              vérifier tes preuves avant de cliquer sur « Vérifier ».
            </p>
          </div>
        </aside>
      </div>
    </main>
  )
}

export default MissionDetail
