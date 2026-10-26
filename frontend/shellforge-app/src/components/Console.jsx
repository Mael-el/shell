import { useRef, useState } from 'react'
import { api } from '../session'

const Console = ({ sessionId, missionId, onAfterRun }) => {
  const [command, setCommand] = useState('')
  const [entries, setEntries] = useState([])
  const [running, setRunning] = useState(false)
  const [error, setError] = useState(null)
  const inputRef = useRef(null)
  const historyRef = useRef([])
  const [historyIndex, setHistoryIndex] = useState(-1)

  const execute = async () => {
    const trimmed = command.trim()
    if (!trimmed || running) return
    setRunning(true)
    setError(null)
    historyRef.current = [trimmed, ...historyRef.current].slice(0, 100)
    setHistoryIndex(-1)
    try {
      const data = await api('/api/labs/run', {
        method: 'POST',
        body: JSON.stringify({ session_id: sessionId, mission_id: missionId, command: trimmed }),
      })
      setEntries((current) => [
        ...current,
        {
          id: `${Date.now()}-${current.length}`,
          command: trimmed,
          stdout: data.stdout,
          stderr: data.stderr,
          exitCode: data.exit_code,
        },
      ])
      setCommand('')
      await onAfterRun?.()
    } catch (err) {
      setError(err.message)
    } finally {
      setRunning(false)
      inputRef.current?.focus()
    }
  }

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      execute()
      return
    }
    if (event.key === 'ArrowUp') {
      event.preventDefault()
      const nextIndex = Math.min(historyIndex + 1, historyRef.current.length - 1)
      if (nextIndex >= 0) {
        setHistoryIndex(nextIndex)
        setCommand(historyRef.current[nextIndex])
      }
      return
    }
    if (event.key === 'ArrowDown') {
      event.preventDefault()
      const nextIndex = historyIndex - 1
      setHistoryIndex(nextIndex)
      setCommand(nextIndex >= 0 ? historyRef.current[nextIndex] : '')
    }
  }

  return (
    <div className="console">
      <div className="console-head">
        <span className="dot dot-red" />
        <span className="dot dot-amber" />
        <span className="dot dot-green" />
        <span className="console-title">shellforge-lab — {missionId}</span>
        <button type="button" className="link-btn" onClick={() => setEntries([])}>
          effacer
        </button>
      </div>

      <div className="console-body">
        {entries.length === 0 && (
          <p className="console-hint">
            Exécute une commande (Entrée). ↑ / ↓ pour l'historique, Maj+Entrée pour un retour à la ligne.
          </p>
        )}
        {entries.map((entry) => (
          <div key={entry.id} className="console-entry">
            <div className="console-command">
              <span className="prompt">$</span> {entry.command}
            </div>
            {entry.stdout && <pre className="console-stdout">{entry.stdout}</pre>}
            {entry.stderr && <pre className="console-stderr">{entry.stderr}</pre>}
            <span className={`exit ${entry.exitCode === 0 ? 'ok' : 'ko'}`}>exit {entry.exitCode}</span>
          </div>
        ))}
      </div>

      <div className="console-input-row">
        <span className="prompt">$</span>
        <textarea
          ref={inputRef}
          rows={1}
          value={command}
          onChange={(event) => setCommand(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="ls -la, cat srv/etc/passwd, ./script.sh…"
          spellCheck="false"
        />
        <button type="button" className="btn btn-small" onClick={execute} disabled={running || !command.trim()}>
          {running ? '…' : 'Exécuter'}
        </button>
      </div>
      {error && <p className="console-error">{error}</p>}
    </div>
  )
}

export default Console
