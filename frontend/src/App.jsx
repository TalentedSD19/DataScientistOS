import { useEffect, useRef, useState } from 'react'
import './App.css'
import { agentOf } from './agents'
import PipelineGraph from './PipelineGraph'

const TERMINAL_STATUSES = ['done', 'error', 'stopped']

// Change this if the backend runs somewhere other than the default dev port.
const API = 'http://127.0.0.1:8000'

function countVisits(logs) {
  const counts = {}
  for (const line of logs) {
    const agent = agentOf(line)
    if (agent) counts[agent.id] = (counts[agent.id] || 0) + 1
  }
  return counts
}

function FileChips({ files, onRemove }) {
  if (files.length === 0) return null
  return (
    <ul className="file-chips">
      {files.map((f, i) => (
        <li key={i}>
          {f.name}
          <button type="button" aria-label={`remove ${f.name}`} onClick={() => onRemove(i)}>×</button>
        </li>
      ))}
    </ul>
  )
}

function Terminal({ logs, running }) {
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ block: 'end' })
  }, [logs])

  return (
    <div className="terminal">
      <div className="terminal-bar">
        <span className="dot dot-red" />
        <span className="dot dot-yellow" />
        <span className="dot dot-green" />
        <span className="terminal-title">logs</span>
      </div>
      <div className="terminal-body">
        {logs.length === 0 && <p className="terminal-empty">waiting for the run to start…</p>}
        {logs.map((line, i) => {
          const agent = agentOf(line)
          const isError = line.startsWith('error:')
          const rest = agent ? line.slice(line.indexOf(':') + 1).trim() : line
          return (
            <div className="terminal-line" key={i}>
              <span className="terminal-prompt">$</span>
              {agent && <span className="terminal-tag" style={{ color: agent.color }}>{agent.id}</span>}
              <span className={isError ? 'terminal-error' : undefined}>{rest}</span>
            </div>
          )
        })}
        {running && <span className="terminal-cursor" aria-hidden="true">▌</span>}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}

const BANNER_TEXT = {
  success: 'Run succeeded',
  failure: 'Run failed',
  stopped: 'Run stopped',
}

function ResultBanner({ outcome, task }) {
  if (!outcome) return null

  const logs = task.logs || []
  const lastError = [...logs].reverse().find((l) => l.startsWith('error:'))
  const gaveUp = [...logs].reverse().find((l) => l.includes('giving up'))

  let detail
  if (outcome === 'success') {
    detail = 'The verifier confirmed the answer is complete.'
  } else if (outcome === 'stopped') {
    detail = 'You stopped this run before it finished.'
  } else if (lastError) {
    detail = lastError.replace(/^error:\s*/, '')
  } else if (gaveUp) {
    detail = 'The code kept crashing, so the executor gave up.'
  } else {
    detail = "Ran out of steps without a verified answer."
  }

  return (
    <div className={`result-banner ${outcome}`}>
      <strong>{BANNER_TEXT[outcome]}</strong>
      <span>{detail}</span>
    </div>
  )
}

// Files worth showing to the user: what the agents produced, not the
// files they were given or internal bookkeeping.
function isDownloadable(path) {
  return !path.startsWith('input/') && !path.startsWith('state/')
}

function ArtifactList({ taskId, files }) {
  const downloadable = files.filter(isDownloadable)
  if (downloadable.length === 0) return <p className="empty">No files were created.</p>

  return (
    <ul className="artifact-list">
      {downloadable.map((path) => (
        <li key={path}>
          <span className="artifact-name">{path}</span>
          <a className="btn btn-secondary" href={`${API}/tasks/${taskId}/artifacts/${path}`} download>
            Download
          </a>
        </li>
      ))}
    </ul>
  )
}

export default function App() {
  const [prompt, setPrompt] = useState('')
  const [files, setFiles] = useState([])
  const [taskId, setTaskId] = useState(null)
  const [task, setTask] = useState(null)
  const [artifacts, setArtifacts] = useState([])
  const [starting, setStarting] = useState(false)
  const [stopping, setStopping] = useState(false)

  const finished = task && TERMINAL_STATUSES.includes(task.status)
  const running = task && !finished

  // Poll the task's status while it's running.
  useEffect(() => {
    if (!taskId || !running) return

    const timer = setInterval(async () => {
      const res = await fetch(`${API}/tasks/${taskId}`)
      const data = await res.json()
      setTask(data)
    }, 1200)

    return () => clearInterval(timer)
  }, [taskId, running])

  // Once the task finishes (however it finished), fetch whatever files it produced.
  useEffect(() => {
    if (!finished) return

    fetch(`${API}/tasks/${taskId}/artifacts`)
      .then((res) => res.json())
      .then((data) => setArtifacts(data.files || []))
  }, [finished, taskId])

  async function handleRun() {
    setStarting(true)
    const form = new FormData()
    form.append('prompt', prompt)
    files.forEach((f) => form.append('files', f))

    const res = await fetch(`${API}/tasks`, { method: 'POST', body: form })
    const data = await res.json()

    setTaskId(data.task_id)
    setTask({ status: data.status, logs: [] })
    setArtifacts([])
    setStarting(false)
  }

  async function handleStop() {
    setStopping(true)
    await fetch(`${API}/tasks/${taskId}/stop`, { method: 'POST' })
  }

  function handleReset() {
    setTaskId(null)
    setTask(null)
    setArtifacts([])
    setPrompt('')
    setFiles([])
    setStopping(false)
  }

  const activeAgent = task?.status ?? null
  const counts = countVisits(task?.logs || [])
  const outcome = !task
    ? null
    : task.status === 'error'
    ? 'failure'
    : task.status === 'stopped'
    ? 'stopped'
    : task.status === 'done'
    ? (task.verifier_status === 'SUFFICIENT' ? 'success' : 'failure')
    : null

  return (
    <div className="app">
      <header className="app-header">
        <h1>DataScientistOS</h1>
        <p>Upload data, describe what you want, and watch the agents work through it.</p>
      </header>

      <ResultBanner outcome={outcome} task={task || {}} />

      <main>
        <section className="left">
          <div className="panel form-panel">
            <label className="field-label" htmlFor="prompt">What do you want to do?</label>
            <textarea
              id="prompt"
              placeholder="e.g. clean this dataset and plot revenue by month"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              disabled={running}
              rows={3}
            />

            <label className="field-label file-label">
              Add files
              <input
                type="file"
                multiple
                onChange={(e) => setFiles(Array.from(e.target.files))}
                disabled={running}
              />
            </label>
            <FileChips files={files} onRemove={(i) => setFiles(files.filter((_, idx) => idx !== i))} />

            <div className="form-actions">
              {!task && (
                <button className="btn btn-primary" disabled={!prompt.trim() || starting} onClick={handleRun}>
                  {starting ? 'Starting…' : 'Run'}
                </button>
              )}
              {finished && (
                <button className="btn btn-primary" onClick={handleReset}>Run another</button>
              )}
              {running && (
                <button className="btn btn-stop" disabled={stopping} onClick={handleStop}>
                  {stopping ? 'Stopping…' : 'Stop'}
                </button>
              )}
              {running && <span className="running-indicator"><span className="spinner" /> running…</span>}
            </div>
          </div>

          <div className="panel">
            <h2 className="panel-title">Pipeline</h2>
            <PipelineGraph activeAgent={activeAgent} counts={counts} outcome={outcome} />
          </div>

          {finished && (
            <div className="panel">
              <h2 className="panel-title">Files created</h2>
              <ArtifactList taskId={taskId} files={artifacts} />
            </div>
          )}
        </section>

        <section className="right">
          <Terminal logs={task?.logs || []} running={!!running} />
        </section>
      </main>
    </div>
  )
}
