import React, { useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { Streamlit, withStreamlitConnection } from 'streamlit-component-lib'

function App({ args }) {
  const days = useMemo(() => JSON.parse(args.days || '[]'), [args.days])
  const grid = useMemo(() => JSON.parse(args.grid || '{}'), [args.grid])
  const initial = useMemo(() => JSON.parse(args.selected_slots || '[]'), [args.selected_slots])
  const [selected, setSelected] = useState(new Set(initial.map((x) => `${x[0]}-${x[1]}`)))
  const [mouseDown, setMouseDown] = useState(false)
  const [lastCell, setLastCell] = useState(null)
  const [dragMode, setDragMode] = useState('add')
  const [activeButton, setActiveButton] = useState(0)


  useEffect(() => {
    const payload = Array.from(selected).map((k) => k.split('-').map(Number))
    Streamlit.setComponentValue(payload)
  }, [selected])

  useEffect(() => {
    Streamlit.setFrameHeight(780)
  }, [])

  useEffect(() => {
  const preventMiddleClick = (e) => {
    if (e.button === 1) {
      e.preventDefault()
    }
  }

  window.addEventListener('mousedown', preventMiddleClick)
  window.addEventListener('auxclick', preventMiddleClick)

  return () => {
    window.removeEventListener('mousedown', preventMiddleClick)
    window.removeEventListener('auxclick', preventMiddleClick)
  }
}, [])

  const toggle = (key, force = null) => {
    setSelected((prev) => {
      const next = new Set(prev)
      if (force === true) next.add(key)
      else if (force === false) next.delete(key)
      else if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

const onDown = (e, d, h) => {
  // Ignore anything except left click
  if (e.button !== 0) {
    e.preventDefault()

    // Middle click clears all
    if (e.button === 1) {
      setMouseDown(false)
      setActiveButton(null)
      setSelected(new Set())
    }

    return
  }

  const shiftKey = e.shiftKey
  const key = `${d}-${h}`

  setMouseDown(true)
  setActiveButton(0)

  setDragMode(selected.has(key) ? 'remove' : 'add')

  if (shiftKey && lastCell) {
    const [ld, lh] = lastCell.split('-').map(Number)

    const minD = Math.min(ld, d)
    const maxD = Math.max(ld, d)

    const minH = Math.min(lh, h)
    const maxH = Math.max(lh, h)

    setSelected(prev => {
      const next = new Set(prev)

      for (let dd = minD; dd <= maxD; dd++) {
        for (let hh = minH; hh <= maxH; hh++) {
          const rangeKey = `${dd}-${hh}`

          if (next.has(rangeKey)) {
            next.delete(rangeKey)
          } else {
            next.add(rangeKey)
          }
        }
      }

      return next
    })
  } else {
    toggle(key)
  }

  setLastCell(key)
}

  return <div onMouseUp={() => setMouseDown(false)} onContextMenu={(e) => e.preventDefault()} style={{ userSelect: 'none' }}>
    <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
      <thead><tr><th style={th}>Hour</th>{days.map((d) => <th key={d} style={th}>{d}</th>)}</tr></thead>
      <tbody>{Array.from({ length: 24 }, (_, h) => <tr key={h}><td style={th}>{String(h).padStart(2, '0')}:00</td>{Array.from({ length: 7 }, (_, d) => {
        const key = `${d}-${h}`
        const type = grid[key] || 'free'
        const colors = { free: '#1f2937', blocked: '#dc2626', study: '#16a34a', due: '#eab308' }
        return <td key={key}
          onMouseDown={(e) => onDown(e, d, h)}
          onMouseEnter={() => {
            if (mouseDown && activeButton === 0) {
              toggle(key, dragMode === 'add')
              setLastCell(key)
            }
          }}
          style={{ border: '1px solid #333', height: 24, background: colors[type], boxShadow: selected.has(key) ? 'inset 0 0 0 3px #2563eb' : 'none' }} />
      })}</tr>)}</tbody>
    </table>
  </div>
}

const th = { border: '1px solid #333', background: '#111', color: '#fff', padding: 4 }
const Connected = withStreamlitConnection(App)
createRoot(document.getElementById('root')).render(<Connected />)
