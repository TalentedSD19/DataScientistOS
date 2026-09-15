import { AGENTS, SANDBOX, AGENT_BY_ID } from './agents'

// Fixed positions for every box in the diagram (an SVG viewBox is resolution
// independent, so hand-placed coordinates are fine here).
const TOP_Y = 55
const BOTTOM_Y = 195
const BOX_W = 108
const BOX_H = 44
const VIEW_W = 1120
const VIEW_H = 250

const POS = {
  sandbox: [70, TOP_Y],
  analyzer: [210, TOP_Y],
  retriever: [350, TOP_Y],
  planner: [490, TOP_Y],
  coder: [630, TOP_Y],
  executor: [770, TOP_Y],
  verifier: [910, TOP_Y],
  end: [1050, TOP_Y],
  debugger: [770, BOTTOM_Y],
  router: [590, BOTTOM_Y],
}

const TOP_ROW = ['sandbox', 'analyzer', 'retriever', 'planner', 'coder', 'executor', 'verifier', 'end']

function Node({ x, y, label, color, active, count, dashed }) {
  const fillOpacity = active ? 1 : count ? 0.16 : 0.05
  return (
    <g>
      <rect
        x={x - BOX_W / 2}
        y={y - BOX_H / 2}
        width={BOX_W}
        height={BOX_H}
        rx={7}
        fill={color}
        fillOpacity={fillOpacity}
        stroke={color}
        strokeWidth={active ? 2.5 : 1.5}
        strokeDasharray={dashed ? '4 3' : undefined}
        className={active ? 'node-active' : undefined}
        style={{ color }}
      />
      <text x={x} y={y + 5} textAnchor="middle" fontSize="14" fontWeight={active ? 600 : 500}
        fill={active ? '#fff' : 'var(--text)'}>
        {label}
      </text>
      {count > 1 && (
        <g>
          <circle cx={x + BOX_W / 2 - 4} cy={y - BOX_H / 2 - 4} r={9} fill={color} />
          <text x={x + BOX_W / 2 - 4} y={y - BOX_H / 2 - 1} textAnchor="middle" fontSize="10"
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
          <marker id="arrow-neutral" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M0,0 L10,5 L0,10 z" fill="#9aa1b0" />
          </marker>
          <marker id="arrow-amber" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M0,0 L10,5 L0,10 z" fill="#fb923c" />
          </marker>
          <marker id="arrow-pink" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
            <path d="M0,0 L10,5 L0,10 z" fill="#f472b6" />
          </marker>
          <pattern id="blueprint-grid" width="24" height="24" patternUnits="userSpaceOnUse">
            <circle cx="1" cy="1" r="1" fill="#c7cdd8" />
          </pattern>
        </defs>

        <rect x="0" y="0" width={VIEW_W} height={VIEW_H} fill="url(#blueprint-grid)" />

        {/* main flow: one straight arrow between each pair of top-row boxes */}
        {TOP_ROW.slice(0, -1).map((id, i) => {
          const nextId = TOP_ROW[i + 1]
          const x1 = POS[id][0] + BOX_W / 2 + 4
          const x2 = POS[nextId][0] - BOX_W / 2 - 4
          return (
            <line key={id} x1={x1} y1={TOP_Y} x2={x2} y2={TOP_Y}
              stroke="#9aa1b0" strokeWidth="2" markerEnd="url(#arrow-neutral)" />
          )
        })}

        {/* retry loop: executor <-> debugger */}
        <path d="M750,77 C700,105 700,150 750,173" fill="none" stroke="#fb923c" strokeWidth="2" strokeDasharray="5 4" markerEnd="url(#arrow-amber)" />
        <path d="M790,173 C840,150 840,105 790,77" fill="none" stroke="#fb923c" strokeWidth="2" strokeDasharray="5 4" markerEnd="url(#arrow-amber)" />

        {/* backtrack loop: verifier -> router -> planner */}
        <path d="M882,76 C 820,128 730,155 638,172" fill="none" stroke="#f472b6" strokeWidth="2" strokeDasharray="5 4" markerEnd="url(#arrow-pink)" />
        <path d="M544,172 C 525,148 513,112 512,81" fill="none" stroke="#f472b6" strokeWidth="2" strokeDasharray="5 4" markerEnd="url(#arrow-pink)" />

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
