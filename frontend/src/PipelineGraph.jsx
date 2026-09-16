import { AGENTS, SANDBOX, AGENT_BY_ID } from './agents'

// Mirrors the reference diagram: a steady top row (sandbox through coder),
// a drop down to the executor, then a steady bottom row running back
// leftward to the end. Two dashed loops hang off that spine -- debugger
// retries the executor directly below it, router backtracks up to the
// planner -- each in its own lane so nothing crosses the main flow.
const BOX_W = 176
const BOX_H = 66

const TOP_Y = 120
const BOT_Y = 470
const DBG_Y = 630
const ROUTER_Y = 300

const POS = {
  sandbox: [150, TOP_Y],
  analyzer: [445, TOP_Y],
  retriever: [740, TOP_Y],
  planner: [1035, TOP_Y],
  coder: [1330, TOP_Y],
  executor: [1330, BOT_Y],
  verifier: [955, BOT_Y],
  reporter: [610, BOT_Y],
  end: [150, BOT_Y],
  router: [995, ROUTER_Y],
  debugger: [1330, DBG_Y],
}

const VIEW_W = 1480
const VIEW_H = 720

function hline(fromId, toId, y) {
  const x1 = POS[fromId][0] + BOX_W / 2 + 6
  const x2 = POS[toId][0] - BOX_W / 2 - 6
  return <line key={`${fromId}-${toId}`} x1={x1} y1={y} x2={x2} y2={y} stroke="#9aa1b0" strokeWidth="2.5" markerEnd="url(#arrow-neutral)" />
}

function hlineRev(fromId, toId, y) {
  const x1 = POS[fromId][0] - BOX_W / 2 - 6
  const x2 = POS[toId][0] + BOX_W / 2 + 6
  return <line key={`${fromId}-${toId}`} x1={x1} y1={y} x2={x2} y2={y} stroke="#9aa1b0" strokeWidth="2.5" markerEnd="url(#arrow-neutral)" />
}

function Node({ x, y, label, color, active, count, dashed }) {
  const fillOpacity = active ? 1 : count ? 0.24 : 0.13
  return (
    <g>
      <rect
        x={x - BOX_W / 2}
        y={y - BOX_H / 2}
        width={BOX_W}
        height={BOX_H}
        rx={12}
        fill={color}
        fillOpacity={fillOpacity}
        stroke={color}
        strokeWidth={active ? 3 : 1.75}
        strokeDasharray={dashed ? '5 4' : undefined}
        className={active ? 'node-active' : undefined}
        style={{ color }}
      />
      <text x={x} y={y + 8} textAnchor="middle" fontSize="27" fontWeight={active ? 600 : 500}
        fill={active ? '#fff' : 'var(--text)'}>
        {label}
      </text>
      {count > 1 && (
        <g>
          <circle cx={x + BOX_W / 2 - 8} cy={y - BOX_H / 2 - 8} r={14} fill={color} />
          <text x={x + BOX_W / 2 - 8} y={y - BOX_H / 2 - 3} textAnchor="middle" fontSize="15"
            fontWeight="600" fill="#fff">
            {count}
          </text>
        </g>
      )}
    </g>
  )
}

export default function PipelineGraph({ activeAgent, counts, outcome }) {
  const endLabel = { success: 'Success', failure: 'Failed', stopped: 'Stopped' }[outcome] || 'End'
  const endColor = { success: 'var(--success)', failure: 'var(--failure)', stopped: '#64748b' }[outcome] || '#9aa1b0'

  const active = AGENT_BY_ID[activeAgent]
  const caption = active && !outcome ? `Right now: ${active.description}` : null

  return (
    <div className="graph-wrap">
      {caption && <p className="graph-caption">{caption}</p>}

      <svg viewBox={`0 0 ${VIEW_W} ${VIEW_H}`} className="graph-svg" role="img" aria-label="agent pipeline diagram">
        <defs>
          <marker id="arrow-neutral" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
            <path d="M0,0 L10,5 L0,10 z" fill="#9aa1b0" />
          </marker>
          <marker id="arrow-amber" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
            <path d="M0,0 L10,5 L0,10 z" fill="#fb923c" />
          </marker>
          <marker id="arrow-pink" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="8" markerHeight="8" orient="auto-start-reverse">
            <path d="M0,0 L10,5 L0,10 z" fill="#f472b6" />
          </marker>
          <pattern id="blueprint-grid" width="26" height="26" patternUnits="userSpaceOnUse">
            <circle cx="1" cy="1" r="1.2" fill="#c7cdd8" />
          </pattern>
        </defs>

        <rect x="0" y="0" width={VIEW_W} height={VIEW_H} rx="16" fill="url(#blueprint-grid)" />

        {/* top row: the steady march forward */}
        {hline('sandbox', 'analyzer', TOP_Y)}
        {hline('analyzer', 'retriever', TOP_Y)}
        {hline('retriever', 'planner', TOP_Y)}
        {hline('planner', 'coder', TOP_Y)}

        {/* drop down into the executor */}
        <line x1={POS.coder[0]} y1={TOP_Y + BOX_H / 2 + 4} x2={POS.executor[0]} y2={BOT_Y - BOX_H / 2 - 4}
          stroke="#9aa1b0" strokeWidth="2.5" markerEnd="url(#arrow-neutral)" />

        {/* bottom row: runs back leftward to the end */}
        {hlineRev('executor', 'verifier', BOT_Y)}
        {hlineRev('verifier', 'reporter', BOT_Y)}
        {hlineRev('reporter', 'end', BOT_Y)}

        {/* debugger retry loop: straight down from executor, straight back up */}
        <path d={`M${POS.executor[0] - 26},${BOT_Y + BOX_H / 2} C ${POS.executor[0] - 40},${(BOT_Y + DBG_Y) / 2} ${POS.debugger[0] - 40},${(BOT_Y + DBG_Y) / 2} ${POS.debugger[0] - 26},${DBG_Y - BOX_H / 2}`}
          fill="none" stroke="#fb923c" strokeWidth="2.5" strokeDasharray="6 5" markerEnd="url(#arrow-amber)" />
        <path d={`M${POS.debugger[0] + 26},${DBG_Y - BOX_H / 2} C ${POS.debugger[0] + 40},${(BOT_Y + DBG_Y) / 2} ${POS.executor[0] + 40},${(BOT_Y + DBG_Y) / 2} ${POS.executor[0] + 26},${BOT_Y + BOX_H / 2}`}
          fill="none" stroke="#fb923c" strokeWidth="2.5" strokeDasharray="6 5" markerEnd="url(#arrow-amber)" />

        {/* router backtrack loop: verifier up to router, router up to planner */}
        <line x1={POS.verifier[0] - 20} y1={BOT_Y - BOX_H / 2} x2={POS.router[0] - 20} y2={ROUTER_Y + BOX_H / 2}
          fill="none" stroke="#f472b6" strokeWidth="2.5" strokeDasharray="6 5" markerEnd="url(#arrow-pink)" />
        <line x1={POS.router[0] + 20} y1={ROUTER_Y - BOX_H / 2} x2={POS.planner[0] - 10} y2={TOP_Y + BOX_H / 2}
          fill="none" stroke="#f472b6" strokeWidth="2.5" strokeDasharray="6 5" markerEnd="url(#arrow-pink)" />

        <Node
          x={POS.sandbox[0]}
          y={POS.sandbox[1]}
          label={SANDBOX.label}
          color={SANDBOX.color}
          active={activeAgent === SANDBOX.id}
        />

        {AGENTS.map((agent) => {
          const [x, y] = POS[agent.id]
          return (
            <Node
              key={agent.id}
              x={x}
              y={y}
              label={agent.label}
              color={agent.color}
              active={activeAgent === agent.id}
              count={counts[agent.id] || 0}
            />
          )
        })}

        <Node x={POS.end[0]} y={POS.end[1]} label={endLabel} color={endColor} active={!!outcome} dashed={!outcome} />
      </svg>

      <ul className="graph-legend">
        <li><span className="swatch swatch-amber" /> retries when the code crashes, up to 3 times before giving up</li>
        <li><span className="swatch swatch-pink" /> loops back through the planner when the answer isn't ready yet</li>
      </ul>
    </div>
  )
}
