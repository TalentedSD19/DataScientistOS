import { AGENTS, SANDBOX, AGENT_BY_ID } from './agents'

// The pipeline is drawn as two lines, like text wrapping: the first half of
// the work (get ready, plan, write code) on line one, the second half (run
// it, check it, report back) on line two. Debugger and router are the two
// retry loops, drawn below as a third, smaller row.
const BOX_W = 150
const BOX_H = 56
const GAP = 190
const ROW1_Y = 60
const ROW2_Y = 300
const LOOP_Y = 460

const ROW1 = ['sandbox', 'analyzer', 'retriever', 'planner', 'coder']
const ROW2 = ['executor', 'verifier', 'reporter', 'end']

const POS = {}
ROW1.forEach((id, i) => { POS[id] = [90 + i * GAP, ROW1_Y] })
ROW2.forEach((id, i) => { POS[id] = [90 + i * GAP, ROW2_Y] })
POS.debugger = [POS.executor[0], LOOP_Y]
POS.router = [380, LOOP_Y]

const VIEW_W = 970
const VIEW_H = 520

function rowLine(id, nextId, y) {
  const x1 = POS[id][0] + BOX_W / 2 + 6
  const x2 = POS[nextId][0] - BOX_W / 2 - 6
  return <line key={id} x1={x1} y1={y} x2={x2} y2={y} stroke="#9aa1b0" strokeWidth="2.5" markerEnd="url(#arrow-neutral)" />
}

function Node({ x, y, label, color, active, count, dashed }) {
  const fillOpacity = active ? 1 : count ? 0.16 : 0.05
  return (
    <g>
      <rect
        x={x - BOX_W / 2}
        y={y - BOX_H / 2}
        width={BOX_W}
        height={BOX_H}
        rx={9}
        fill={color}
        fillOpacity={fillOpacity}
        stroke={color}
        strokeWidth={active ? 3 : 1.75}
        strokeDasharray={dashed ? '5 4' : undefined}
        className={active ? 'node-active' : undefined}
        style={{ color }}
      />
      <text x={x} y={y + 6} textAnchor="middle" fontSize="18" fontWeight={active ? 600 : 500}
        fill={active ? '#fff' : 'var(--text)'}>
        {label}
      </text>
      {count > 1 && (
        <g>
          <circle cx={x + BOX_W / 2 - 6} cy={y - BOX_H / 2 - 6} r={12} fill={color} />
          <text x={x + BOX_W / 2 - 6} y={y - BOX_H / 2 - 2} textAnchor="middle" fontSize="13"
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

        <rect x="0" y="0" width={VIEW_W} height={VIEW_H} fill="url(#blueprint-grid)" />

        {/* line one */}
        {ROW1.slice(0, -1).map((id, i) => rowLine(id, ROW1[i + 1], ROW1_Y))}
        {/* line two */}
        {ROW2.slice(0, -1).map((id, i) => rowLine(id, ROW2[i + 1], ROW2_Y))}

        {/* the wrap from the end of line one to the start of line two */}
        <path
          d={`M${POS.coder[0]},${ROW1_Y + BOX_H / 2 + 4}
              L${POS.coder[0]},${(ROW1_Y + ROW2_Y) / 2}
              L${POS.executor[0]},${(ROW1_Y + ROW2_Y) / 2}
              L${POS.executor[0]},${ROW2_Y - BOX_H / 2 - 6}`}
          fill="none" stroke="#9aa1b0" strokeWidth="2.5" markerEnd="url(#arrow-neutral)"
        />

        {/* retry loop: executor <-> debugger, crashes send it here and back */}
        <path d="M65,332 C15,368 15,412 65,448" fill="none" stroke="#fb923c" strokeWidth="2.5" strokeDasharray="6 5" markerEnd="url(#arrow-amber)" />
        <path d="M115,448 C165,412 165,368 115,332" fill="none" stroke="#fb923c" strokeWidth="2.5" strokeDasharray="6 5" markerEnd="url(#arrow-amber)" />

        {/* backtrack loop: verifier -> router -> planner, sends work back up to line one */}
        <path d="M300,328 C 340,375 360,405 365,432" fill="none" stroke="#f472b6" strokeWidth="2.5" strokeDasharray="6 5" markerEnd="url(#arrow-pink)" />
        <path d="M410,432 C 500,380 610,180 645,90" fill="none" stroke="#f472b6" strokeWidth="2.5" strokeDasharray="6 5" markerEnd="url(#arrow-pink)" />

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
