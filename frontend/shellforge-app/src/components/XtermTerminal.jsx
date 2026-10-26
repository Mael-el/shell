import { useEffect, useRef } from 'react'
import { Terminal } from 'xterm'
import 'xterm/css/xterm.css'
import { FitAddon } from '@xterm/addon-fit'

const XtermTerminal = ({ sessionId, challengeId, onCommand, onReady }) => {
  const terminalRef = useRef(null)
  const terminalInstanceRef = useRef(null)
  const fitAddonRef = useRef(null)

  useEffect(() => {
    if (!terminalRef.current) return

    const terminal = new Terminal({
      cursorBlink: true,
      theme: {
        background: '#020817',
        foreground: '#e2e8f0',
        cursor: '#7dd3fc',
        black: '#0f172a',
        red: '#f87171',
        green: '#4ade80',
        yellow: '#fbbf24',
        blue: '#60a5fa',
      },
      fontFamily: 'SFMono-Regular, Consolas, monospace',
      fontSize: 14,
      lineHeight: 1.3,
      scrollback: 5000,
    })

    const fitAddon = new FitAddon()
    terminal.loadAddon(fitAddon)

    terminal.open(terminalRef.current)
    fitAddon.fit()

    terminal.write('Welcome to SHELLFORGE\r\n$ ')
    terminal.onData((data) => {
      const current = terminal._core.buffer.lines.get(terminal._core.buffer.y)?.get(terminal._core.buffer.x)
      if (data === '\r') {
        const line = terminal.buffer.active.getLine(terminal.buffer.active.cursorY)?.translateToString(true).trim() || ''
        if (line) {
          onCommand(line)
          terminal.write('\r\n$ ')
        }
        return
      }

      if (data === '\u007f') {
        terminal.write('\b \b')
        return
      }

      terminal.write(data)
    })

    terminalInstanceRef.current = terminal
    fitAddonRef.current = fitAddon
    onReady?.(terminal)

    const resizeObserver = new ResizeObserver(() => fitAddon.fit())
    resizeObserver.observe(terminalRef.current)

    return () => {
      resizeObserver.disconnect()
      terminal.dispose()
    }
  }, [challengeId, sessionId, onCommand, onReady])

  useEffect(() => {
    const handleResize = () => fitAddonRef.current?.fit()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])

  return <div ref={terminalRef} className="xterm-root" />
}

export default XtermTerminal
