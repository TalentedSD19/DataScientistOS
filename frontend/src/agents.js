// The infrastructure step that happens before any agent runs.
export const SANDBOX = {
  id: 'sandbox',
  label: 'Sandbox',
  color: '#94a3b8',
  description: 'spinning up an isolated sandbox to run your code',
}

// The agents in the order the backend graph normally runs them, each with
// its own colour so the same agent looks the same in the graph and the logs.
export const AGENTS = [
  { id: 'analyzer', label: 'Analyzer', color: '#60a5fa', description: 'reading and summarizing your files' },
  { id: 'retriever', label: 'Retriever', color: '#38bdf8', description: 'picking which files are relevant' },
  { id: 'planner', label: 'Planner', color: '#a78bfa', description: 'deciding the next step' },
  { id: 'coder', label: 'Coder', color: '#fbbf24', description: 'writing the analysis code' },
  { id: 'executor', label: 'Executor', color: '#34d399', description: 'running the code' },
  { id: 'debugger', label: 'Debugger', color: '#fb923c', description: 'fixing the code that just crashed' },
  { id: 'verifier', label: 'Verifier', color: '#22d3ee', description: 'checking whether the answer is complete' },
  { id: 'router', label: 'Router', color: '#f472b6', description: 'deciding whether to add a step or backtrack' },
]

export const AGENT_BY_ID = Object.fromEntries([SANDBOX, ...AGENTS].map((a) => [a.id, a]))

// Every log line is written as "agentname: message" (see backend/agents/*.py,
// and "sandbox: ..." from backend/runner.py), so the prefix before the first
// colon tells us which step it came from.
export function agentOf(logLine) {
  const name = logLine.split(':')[0].trim()
  return AGENT_BY_ID[name] || null
}
