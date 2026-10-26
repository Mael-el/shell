import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { apiUrl } from '../config'
import XtermTerminal from './XtermTerminal'

const SESSION_KEY = 'shellforge_session_id'

const ChallengeDetail = () => {
  const { moduleId, challengeId } = useParams()
  const [module, setModule] = useState(null)
  const [challenge, setChallenge] = useState(null)
  const [answer, setAnswer] = useState('')
  const [labCommand, setLabCommand] = useState('')
  const [labOutput, setLabOutput] = useState('')
  const [terminalTabs, setTerminalTabs] = useState([])
  const [activeTerminalId, setActiveTerminalId] = useState(null)
  const [terminalHistory, setTerminalHistory] = useState([])
  const [labFiles, setLabFiles] = useState([])
  const [selectedLabFile, setSelectedLabFile] = useState(null)
  const [xtermTerminal, setXtermTerminal] = useState(null)
  const [scriptName, setScriptName] = useState('solution.sh')
  const [scriptContent, setScriptContent] = useState('#!/usr/bin/env bash\n')
  const [sessionId, setSessionId] = useState('')
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [labRunning, setLabRunning] = useState(false)
  const [error, setError] = useState(null)
  const [result, setResult] = useState(null)
  const [learningEngine, setLearningEngine] = useState(null)
  const [learningProgress, setLearningProgress] = useState({ total_sections: 0, completed_sections: 0, progress_percent: 0, sections: [] })
  const [courseView, setCourseView] = useState('overview')

  useEffect(() => {
    const loadChallenge = async () => {
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

        const challengeRes = await fetch(apiUrl(`/api/challenges/${challengeId}`))
        if (!challengeRes.ok) throw new Error('Impossible de charger la mission')
        const foundChallenge = await challengeRes.json()

        if (foundChallenge.module_id !== moduleId) {
          throw new Error('Mission introuvable dans ce module')
        }
        setChallenge(foundChallenge)
        setLearningEngine(foundChallenge.learning_engine || null)
        setLearningProgress({ total_sections: 0, completed_sections: 0, progress_percent: 0, sections: [] })
        setLabCommand(foundChallenge.command || '')
        setScriptName(`${foundChallenge.id}.sh`)
        setScriptContent('#!/usr/bin/env bash\n')
        setLabFiles([])
        setSelectedLabFile(null)

        const storedTerminalState = JSON.parse(localStorage.getItem(`shellforge_terminal_state_${foundChallenge.id}`) || 'null') || {
          tabs: [{ id: 'terminal-1', name: 'Terminal 1', history: [] }],
          activeTerminalId: 'terminal-1',
        }
        setTerminalTabs(storedTerminalState.tabs)
        setActiveTerminalId(storedTerminalState.activeTerminalId || storedTerminalState.tabs[0]?.id || 'terminal-1')
        setTerminalHistory(storedTerminalState.tabs[0]?.history || [])
        localStorage.setItem('shellforge_last_challenge', JSON.stringify({
          moduleId,
          challengeId: foundChallenge.id,
          title: foundChallenge.title,
          path: `/module/${moduleId}/challenge/${foundChallenge.id}`,
          updatedAt: Date.now(),
        }))

        let activeSessionId = localStorage.getItem(SESSION_KEY)
        if (!activeSessionId) {
          const sessionRes = await fetch(apiUrl('/api/sessions'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: 'shellforge-user' })
          })
          if (!sessionRes.ok) throw new Error('Impossible de créer une session')
          const sessionData = await sessionRes.json()
          activeSessionId = sessionData.session_id
          localStorage.setItem(SESSION_KEY, activeSessionId)
        }
        setSessionId(activeSessionId)

        const filesRes = await fetch(apiUrl(`/api/labs/files?session_id=${encodeURIComponent(activeSessionId)}&working_dir=${encodeURIComponent(foundChallenge.id)}`))
        if (!filesRes.ok) throw new Error('Impossible de charger les fichiers du laboratoire')
        const filesData = await filesRes.json()
        setLabFiles(filesData.entries)

        if (foundChallenge.learning_engine) {
          const progressRes = await fetch(apiUrl(`/api/challenges/${foundChallenge.id}/learning-progress?session_id=${activeSessionId}`))
          if (progressRes.ok) {
            const progressData = await progressRes.json()
            setLearningProgress(progressData)
          }
        }
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    loadChallenge()
  }, [moduleId, challengeId])

  const persistTerminalState = (nextTabs, nextActiveId, nextHistory) => {
    if (!challenge) return
    const payload = {
      tabs: nextTabs,
      activeTerminalId: nextActiveId,
      history: nextHistory,
    }
    localStorage.setItem(`shellforge_terminal_state_${challenge.id}`, JSON.stringify(payload))
  }

  const refreshLabFiles = async () => {
    if (!sessionId || !challenge) return
    const response = await fetch(apiUrl(`/api/labs/files?session_id=${encodeURIComponent(sessionId)}&working_dir=${encodeURIComponent(challenge.id)}`))
    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new Error(data.detail || 'Impossible d’actualiser les fichiers du laboratoire')
    }
    const data = await response.json()
    setLabFiles(data.entries)
  }

  const handleRefreshLabFiles = async () => {
    try {
      await refreshLabFiles()
      setError(null)
    } catch (err) {
      setError(err.message)
    }
  }

  const handleLabRun = async () => {
    if (!sessionId || !challenge) {
      setError('Session ou mission incomplète')
      return
    }

    if (!labCommand.trim()) {
      setError('Saisis une commande avant d’exécuter le laboratoire.')
      return
    }

    setLabRunning(true)
    setError(null)

    try {
      const response = await fetch(apiUrl('/api/labs/run'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          command: labCommand,
          working_dir: challenge.id
        })
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail || 'Échec de l’exécution du laboratoire')
      }

      const data = await response.json()
      const renderedOutput = [
        `$ ${labCommand}`,
        data.stdout ? data.stdout.trim() : '',
        data.stderr ? data.stderr.trim() : '',
        `[exit ${data.exit_code}]`
      ].filter(Boolean).join('\n')

      const entry = {
        command: labCommand,
        output: renderedOutput,
        exitCode: data.exit_code,
        timestamp: Date.now(),
      }

      const nextTabs = terminalTabs.map((tab) => {
        if (tab.id !== activeTerminalId) return tab
        return { ...tab, history: [...(tab.history || []), entry] }
      })
      const nextHistory = nextTabs.find((tab) => tab.id === activeTerminalId)?.history || []

      setTerminalTabs(nextTabs)
      setTerminalHistory(nextHistory)
      persistTerminalState(nextTabs, activeTerminalId, nextHistory)
      setLabOutput(renderedOutput)
      setAnswer(data.stdout || '')
      await refreshLabFiles()
    } catch (err) {
      setError(err.message)
      setLabOutput('')
    } finally {
      setLabRunning(false)
    }
  }

  const handleResetLab = async () => {
    if (!sessionId || !challenge) {
      setError('Session ou mission incomplète')
      return
    }

    try {
      const response = await fetch(apiUrl('/api/labs/reset'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, working_dir: challenge.id })
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail || 'Échec de la réinitialisation du laboratoire')
      }

      const nextTabs = terminalTabs.map((tab) => ({
        ...tab,
        history: tab.id === activeTerminalId ? [] : tab.history || [],
      }))
      const nextHistory = nextTabs.find((tab) => tab.id === activeTerminalId)?.history || []

      setTerminalTabs(nextTabs)
      setTerminalHistory(nextHistory)
      persistTerminalState(nextTabs, activeTerminalId, nextHistory)
      setLabOutput('Laboratoire réinitialisé : le dossier de travail est propre et prêt pour une nouvelle session.')
      setLabCommand('')
      setSelectedLabFile(null)
      await refreshLabFiles()
      setError(null)
    } catch (err) {
      setError(err.message)
    }
  }

  const handleMarkLesson = async (lessonId, status = 'completed') => {
    if (!sessionId || !challenge) return

    try {
      const response = await fetch(apiUrl('/api/learning/progress'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, challenge_id: challenge.id, lesson_id: lessonId, status })
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail || 'Échec de la mise à jour du cours')
      }

      const data = await response.json()
      setLearningProgress(data)
    } catch (err) {
      setError(err.message)
    }
  }

  const handleAddTerminal = () => {
    const nextId = `terminal-${Date.now()}`
    const nextTab = {
      id: nextId,
      name: `Terminal ${terminalTabs.length + 1}`,
      history: [],
    }
    const nextTabs = [...terminalTabs, nextTab]
    setTerminalTabs(nextTabs)
    setActiveTerminalId(nextId)
    setTerminalHistory([])
    persistTerminalState(nextTabs, nextId, [])
  }

  const handleSelectTerminal = (terminalId) => {
    const selectedTab = terminalTabs.find((tab) => tab.id === terminalId)
    setActiveTerminalId(terminalId)
    setTerminalHistory(selectedTab?.history || [])
    setLabOutput(selectedTab?.history?.[selectedTab.history.length - 1]?.output || '')
    persistTerminalState(terminalTabs, terminalId, selectedTab?.history || [])
  }

  const handleSaveScript = async () => {
    if (!sessionId || !challenge) {
      setError('Session ou mission incomplète')
      return
    }

    try {
      const payload = JSON.stringify(scriptContent)
      const command = `python - <<'PY'
from pathlib import Path
path = Path('${scriptName}')
path.write_text(${payload})
path.chmod(0o755)
PY`

      const response = await fetch(apiUrl('/api/labs/run'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          command,
          working_dir: challenge.id
        })
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail || 'Échec de l’enregistrement du script')
      }

      const data = await response.json()
      setLabOutput([`Script sauvegardé dans ${scriptName}`, data.stdout || '', `[exit ${data.exit_code}]`].filter(Boolean).join('\n'))
      await refreshLabFiles()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleRunScript = async () => {
    if (!sessionId || !challenge) {
      setError('Session ou mission incomplète')
      return
    }

    try {
      const response = await fetch(apiUrl('/api/labs/run'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          command: `./${scriptName}`,
          working_dir: challenge.id
        })
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail || 'Échec de l’exécution du script')
      }

      const data = await response.json()
      const renderedOutput = [
        `$ ./${scriptName}`,
        data.stdout ? data.stdout.trim() : '',
        data.stderr ? data.stderr.trim() : '',
        `[exit ${data.exit_code}]`
      ].filter(Boolean).join('\n')
      setLabOutput(renderedOutput)
      setAnswer(data.stdout || '')
      await refreshLabFiles()
    } catch (err) {
      setError(err.message)
    }
  }

  const handleSubmit = async (event) => {
    event.preventDefault()

    if (!sessionId || !challenge) {
      setError('Session ou mission incomplète')
      return
    }

    setSubmitting(true)
    setError(null)

    try {
      const response = await fetch(apiUrl('/api/submissions'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          challenge_id: challenge.id,
          output: answer,
          command: challenge.command
        })
      })

      if (!response.ok) {
        const data = await response.json().catch(() => ({}))
        throw new Error(data.detail || 'Échec de la validation')
      }

      const data = await response.json()
      setResult(data)
      if (data.correct) {
        localStorage.setItem('shellforge_last_challenge', JSON.stringify({
          moduleId,
          challengeId: challenge.id,
          title: challenge.title,
          path: `/module/${moduleId}/challenge/${challenge.id}`,
          updatedAt: Date.now(),
        }))
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return <div className="dashboard-loading">Chargement de la mission...</div>
  }

  if (error) {
    return (
      <main className="page-shell">
        <div className="panel">
          <p className="eyebrow">Erreur</p>
          <h1>{error}</h1>
          <Link to={`/module/${moduleId}`} className="module-link">Retour au module</Link>
        </div>
      </main>
    )
  }

  return (
    <main className="dashboard-container">
      <header className="header-wrapper">
        <div>
          <p className="eyebrow">Mission</p>
          <h1>{challenge.title}</h1>
        </div>
        <p className="subtitle">{challenge.description}</p>
      </header>

      <section className="stats-grid">
        <div className="stat-card">
          <div className="stat-number">{challenge.points}</div>
          <div className="stat-label">Points</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{challenge.difficulty}</div>
          <div className="stat-label">Difficulté</div>
        </div>
        <div className="stat-card">
          <div className="stat-number">{module.title}</div>
          <div className="stat-label">Module</div>
        </div>
      </section>

      <section className="challenge-shell">
        <div className="challenge-panel">
          <div className="challenge-box">
            <span className="challenge-label">Commande à exécuter</span>
            <pre>{challenge.command}</pre>
          </div>

          {learningEngine && (
            <div className="learning-engine-panel">
              <div className="learning-header-row">
                <div>
                  <p className="eyebrow">SHELLFORGE Learning Engine</p>
                  <h3>{learningEngine.title}</h3>
                </div>
                <div className="learning-tabs">
                  <button type="button" className={courseView === 'overview' ? 'learning-tab active' : 'learning-tab'} onClick={() => setCourseView('overview')}>Cours</button>
                  <button type="button" className={courseView === 'practice' ? 'learning-tab active' : 'learning-tab'} onClick={() => setCourseView('practice')}>Pratique</button>
                </div>
              </div>

              {courseView === 'overview' ? (
                <div className="learning-content">
                  <div className="learning-progress-summary">
                    <div>
                      <small>Progression du cours</small>
                      <strong>{learningProgress.completed_sections}/{learningProgress.total_sections} sections</strong>
                    </div>
                    <div className="learning-progress-bar">
                      <span style={{ width: `${learningProgress.progress_percent || 0}%` }} />
                    </div>
                  </div>

                  <p className="learning-summary">{learningEngine.summary}</p>

                  <div className="learning-block">
                    <h4>Objectifs</h4>
                    <ul>
                      {learningEngine.objectives?.map((goal) => <li key={goal}>{goal}</li>)}
                    </ul>
                  </div>

                  <div className="learning-block">
                    <h4>Pré-requis</h4>
                    <ul>
                      {learningEngine.prerequisites?.map((item) => <li key={item}>{item}</li>)}
                    </ul>
                  </div>

                  <div className="learning-block">
                    <h4>Sections pédagogiques</h4>
                    {learningEngine.sections?.map((section) => {
                      const sectionState = learningProgress.sections.find((item) => item.id === section.id)
                      const isCompleted = sectionState?.status === 'completed'
                      return (
                        <div key={section.id} className="lesson-card">
                          <div className="lesson-card-header">
                            <h5>{section.name}</h5>
                            <button type="button" className="module-link secondary-link" onClick={() => handleMarkLesson(section.id, isCompleted ? 'completed' : 'completed')}>
                              {isCompleted ? 'Lu' : 'Marquer lu'}
                            </button>
                          </div>
                          <p>{section.content}</p>
                        </div>
                      )
                    })}
                  </div>

                  <div className="learning-block">
                    <h4>Références de commandes</h4>
                    {learningEngine.command_reference?.map((item) => (
                      <div key={item.command} className="command-reference">
                        <strong>{item.command}</strong>
                        <span>{item.role}</span>
                        <code>{item.example}</code>
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="learning-content">
                  <div className="learning-block">
                    <h4>Mini-exercices</h4>
                    {learningEngine.exercises?.map((exercise, index) => (
                      <div key={`${exercise.prompt}-${index}`} className="exercise-card">
                        <p>{exercise.prompt}</p>
                        <code>{exercise.expected}</code>
                        <small>Indice : {exercise.hint}</small>
                        <button type="button" className="module-link secondary-link" onClick={() => setLabCommand(exercise.expected)}>Tester dans le terminal</button>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          <div className="terminal-panel">
            <div className="terminal-header">
              <span className="terminal-dot dot-red" />
              <span className="terminal-dot dot-yellow" />
              <span className="terminal-dot dot-green" />
              <span className="terminal-title">shellforge-lab</span>
            </div>

            <div className="terminal-tabs">
              {terminalTabs.map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  className={`terminal-tab ${tab.id === activeTerminalId ? 'active' : ''}`}
                  onClick={() => handleSelectTerminal(tab.id)}
                >
                  {tab.name}
                </button>
              ))}
              <button type="button" className="terminal-tab add-tab" onClick={handleAddTerminal}>+ Nouveau</button>
            </div>

            <label htmlFor="lab-command" className="challenge-label">Commande du laboratoire</label>
            <textarea
              id="lab-command"
              value={labCommand}
              onChange={(event) => setLabCommand(event.target.value)}
              rows={4}
              className="terminal-input"
            />

            <div className="challenge-actions">
              <button type="button" className="module-link secondary-link" onClick={handleLabRun} disabled={labRunning}>
                {labRunning ? 'Exécution...' : 'Exécuter dans le lab'}
              </button>
              <button type="button" className="module-link secondary-link" onClick={handleResetLab}>
                Réinitialiser
              </button>
            </div>

            <div className="terminal-output" aria-live="polite">
              {terminalHistory.length > 0 ? (
                terminalHistory.map((entry) => (
                  <div key={`${entry.timestamp}-${entry.command}`} className="terminal-line">
                    <div className="terminal-command-line">$ {entry.command}</div>
                    <pre className="terminal-entry-output">{entry.output}</pre>
                  </div>
                ))
              ) : (
                labOutput || 'Aucune sortie pour le moment. Lance une commande pour observer le résultat.'
              )}
            </div>

            {xtermTerminal ? (
              <div className="xterm-wrapper">
                <XtermTerminal
                  sessionId={sessionId}
                  challengeId={challenge.id}
                  onCommand={(command) => {
                    setLabCommand(command)
                    setAnswer(command)
                  }}
                  onReady={(terminal) => {
                    setXtermTerminal(terminal)
                    terminal.write('\r\nSHELLFORGE terminal ready\r\n')
                  }}
                />
              </div>
            ) : (
              <XtermTerminal
                sessionId={sessionId}
                challengeId={challenge.id}
                onCommand={(command) => {
                  setLabCommand(command)
                  setAnswer(command)
                }}
                onReady={(terminal) => {
                  setXtermTerminal(terminal)
                  terminal.write('\r\nSHELLFORGE terminal ready\r\n')
                }}
              />
            )}
          </div>

          <div className="file-browser-panel">
            <div className="terminal-header">
              <span className="terminal-dot dot-blue" />
              <span className="terminal-title">Fichiers de la mission</span>
              <button type="button" className="module-link secondary-link" onClick={handleRefreshLabFiles}>Actualiser</button>
            </div>
            <p className="file-browser-help">
              Explore les fichiers d’exercice dans le terminal : ils sont propres à ta session et réinitialisables.
            </p>
            <div className="file-browser-layout">
              <div className="file-browser-list">
                {labFiles.map((entry) => entry.type === 'directory' ? (
                  <div key={entry.path} className="file-browser-entry directory-entry">
                    <span>Dossier</span>
                    <code>{entry.path}</code>
                  </div>
                ) : (
                  <button
                    key={entry.path}
                    type="button"
                    className={`file-browser-entry file-entry ${selectedLabFile?.path === entry.path ? 'active' : ''}`}
                    onClick={() => setSelectedLabFile(entry)}
                  >
                    <span>Fichier</span>
                    <code>{entry.path}</code>
                  </button>
                ))}
              </div>
              <div className="file-preview">
                {selectedLabFile ? (
                  <>
                    <div className="file-preview-header">
                      <strong>{selectedLabFile.path}</strong>
                      <button
                        type="button"
                        className="module-link secondary-link"
                        onClick={() => setLabCommand(`cat -- ${selectedLabFile.path}`)}
                      >
                        Lire dans le terminal
                      </button>
                    </div>
                    <pre>{selectedLabFile.content ?? 'Aperçu indisponible pour ce fichier (taille supérieure à 64 Kio).'}</pre>
                  </>
                ) : (
                  <p>Sélectionne un fichier pour consulter son contenu avant de le manipuler.</p>
                )}
              </div>
            </div>
          </div>

          <div className="script-panel">
            <div className="terminal-header">
              <span className="terminal-dot dot-blue" />
              <span className="terminal-dot dot-yellow" />
              <span className="terminal-dot dot-green" />
              <span className="terminal-title">workspace</span>
            </div>

            <label htmlFor="script-name" className="challenge-label">Nom du script</label>
            <input
              id="script-name"
              className="script-name-input"
              value={scriptName}
              onChange={(event) => setScriptName(event.target.value.trim() || 'solution.sh')}
            />

            <textarea
              value={scriptContent}
              onChange={(event) => setScriptContent(event.target.value)}
              rows={10}
              className="terminal-input"
              placeholder="#!/usr/bin/env bash\n# Ici ton script..."
            />

            <div className="challenge-actions">
              <button type="button" className="module-link secondary-link" onClick={handleSaveScript}>Enregistrer</button>
              <button type="button" className="module-link" onClick={handleRunScript}>Exécuter le script</button>
            </div>
          </div>

          <form onSubmit={handleSubmit} className="challenge-form">
            <label htmlFor="mission-output" className="challenge-label">Sortie de la commande</label>
            <textarea
              id="mission-output"
              value={answer}
              onChange={(event) => setAnswer(event.target.value)}
              placeholder="Collez ici le résultat obtenu dans le terminal..."
              rows={8}
            />

            <div className="challenge-actions">
              <Link to={`/module/${moduleId}`} className="module-link secondary-link">← Retour</Link>
              <button type="submit" className="module-link" disabled={submitting}>
                {submitting ? 'Validation...' : 'Valider la mission'}
              </button>
            </div>
          </form>
        </div>

        <aside className="concept-panel">
          <h3>Leçon à retenir</h3>
          <p>{challenge.theory || 'Cette mission vise à consolider les bases de Bash et la logique de script.'}</p>

          <h3>Indice</h3>
          <p>{challenge.hint || 'Réfléchissez à la commande adéquate et revérifiez la sortie attendue.'}</p>
        </aside>

        {result && (
          <div className={`result-panel ${result.correct ? 'success' : 'error'}`}>
            <h3>{result.correct ? 'Mission validée !' : 'Mission non validée'}</h3>
            <p>
              {result.correct
                ? `+${result.points_earned} XP gagnés.`
                : `Résultat attendu : ${challenge.expected_output || 'non fourni'}`}
            </p>
            {!result.correct && challenge.expected_output && (
              <p className="result-detail">Sortie attendue : {challenge.expected_output}</p>
            )}
          </div>
        )}

        {error && <div className="dashboard-error">{error}</div>}
      </section>
    </main>
  )
}

export default ChallengeDetail
