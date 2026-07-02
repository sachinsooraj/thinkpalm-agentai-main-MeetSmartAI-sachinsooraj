import { useState, useEffect } from 'react'
import axios from 'axios'
import { format } from 'date-fns'
import toast from 'react-hot-toast'
import './MeetingList.css'

const API = '/api'

const STATUS_BADGE = {
  scheduled: 'badge-purple',
  completed: 'badge-green',
  cancelled: 'badge-red',
}

function stringToColor(str) {
  const colors = ['#7c3aed','#059669','#0284c7','#b45309','#be185d','#4338ca','#0891b2','#15803d']
  let hash = 0
  for (let i = 0; i < str.length; i++) hash = str.charCodeAt(i) + ((hash << 5) - hash)
  return colors[Math.abs(hash) % colors.length]
}

export default function MeetingList() {
  const [meetings, setMeetings] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')
  const [expanded, setExpanded] = useState(null)
  const [actionItems, setActionItems] = useState({})
  const [generatingMom, setGeneratingMom] = useState(null)

  const load = async () => {
    setLoading(true)
    try {
      const res = await axios.get(`${API}/meetings/`)
      setMeetings(res.data)
    } catch {
      toast.error('Failed to load meetings')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const filtered = filter === 'all'
    ? meetings
    : meetings.filter(m => m.status === filter)

  const cancel = async (id) => {
    if (!confirm('Cancel this meeting?')) return
    try {
      await axios.post(`${API}/booking/cancel/${id}`)
      toast.success('Meeting cancelled')
      load()
    } catch {
      toast.error('Cancel failed')
    }
  }

  const generateMom = async (id) => {
    setGeneratingMom(id)
    try {
      await axios.post(`${API}/notes/generate-mom/${id}`)
      toast.success('MoM generated and emailed! Check /outputs folder.')
    } catch {
      toast.error('MoM generation failed. Have you processed meeting notes first?')
    } finally {
      setGeneratingMom(null)
    }
  }

  const sendReminder = async (id) => {
    try {
      await axios.post(`${API}/notes/send-reminder/${id}`)
      toast.success('Reminder sent!')
    } catch {
      toast.error('Reminder send failed')
    }
  }

  const loadActions = async (meetingId) => {
    if (actionItems[meetingId]) return
    try {
      const res = await axios.get(`${API}/meetings/${meetingId}/action-items`)
      setActionItems(prev => ({ ...prev, [meetingId]: res.data }))
    } catch {}
  }

  const toggleExpand = (id) => {
    const next = expanded === id ? null : id
    setExpanded(next)
    if (next) loadActions(next)
  }

  return (
    <div className="meetings-page">
      <div className="page-header">
        <h1>Meetings</h1>
        <p>View, manage, and track all ThinkPalm team meetings.</p>
      </div>

      {/* Filter tabs */}
      <div className="filter-tabs mb-4">
        {['all', 'scheduled', 'completed', 'cancelled'].map(f => (
          <button
            key={f}
            id={`filter-${f}`}
            className={`filter-tab ${filter === f ? 'active' : ''}`}
            onClick={() => setFilter(f)}
          >
            {f.charAt(0).toUpperCase() + f.slice(1)}
            <span className="tab-count">
              {f === 'all' ? meetings.length : meetings.filter(m => m.status === f).length}
            </span>
          </button>
        ))}
      </div>

      {loading ? (
        <div className="loading-state">
          <div className="spinner" />
          <span className="text-muted">Loading meetings...</span>
        </div>
      ) : filtered.length === 0 ? (
        <div className="empty-state card">
          <div style={{ fontSize: '3rem', marginBottom: 12, opacity: 0.4 }}>📭</div>
          <h3>No meetings found</h3>
          <p>Book your first meeting to get started.</p>
          <a href="/book" className="btn btn-primary mt-4">Book a Meeting →</a>
        </div>
      ) : (
        <div className="meeting-list">
          {filtered.map(m => (
            <div key={m.id} className={`meeting-card card animate-in ${expanded === m.id ? 'expanded' : ''}`}>
              {/* Card header */}
              <div className="mc-header" onClick={() => toggleExpand(m.id)}>
                <div className="mc-left">
                  <div className="mc-date">
                    <span className="date-day">{format(new Date(m.start_time), 'd')}</span>
                    <span className="date-mon">{format(new Date(m.start_time), 'MMM')}</span>
                  </div>
                  <div className="mc-info">
                    <div className="mc-title">{m.title}</div>
                    <div className="mc-meta">
                      <span>🕐 {format(new Date(m.start_time), 'hh:mm a')} — {format(new Date(m.end_time), 'hh:mm a')}</span>
                      <span>📍 {m.location}</span>
                      <span>👤 {m.organizer?.name}</span>
                    </div>
                    <div className="mc-participants">
                      {m.participants?.slice(0, 5).map(p => (
                        <span
                          key={p.id}
                          className="avatar avatar-sm"
                          style={{ background: stringToColor(p.name) }}
                          title={p.name}
                        >
                          {p.avatar_initials || p.name[0]}
                        </span>
                      ))}
                      {m.participants?.length > 5 && (
                        <span className="avatar avatar-sm" style={{ background: '#334155' }}>
                          +{m.participants.length - 5}
                        </span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="mc-right">
                  <span className={`badge ${STATUS_BADGE[m.status] || 'badge-gray'}`}>
                    {m.status}
                  </span>
                  <span className="expand-icon">{expanded === m.id ? '▲' : '▼'}</span>
                </div>
              </div>

              {/* Expanded details */}
              {expanded === m.id && (
                <div className="mc-body animate-in">
                  {m.agenda && (
                    <div className="mc-section">
                      <div className="section-title">Agenda</div>
                      <pre className="agenda-text">{m.agenda}</pre>
                    </div>
                  )}

                  {/* Action items */}
                  {actionItems[m.id] && actionItems[m.id].length > 0 && (
                    <div className="mc-section">
                      <div className="section-title">Action Items ({actionItems[m.id].length})</div>
                      <div className="action-list">
                        {actionItems[m.id].map(ai => (
                          <div key={ai.id} className={`action-row priority-${ai.priority}`}>
                            <span className={`priority-dot priority-${ai.priority}`} />
                            <span className="action-desc">{ai.description}</span>
                            <span className="action-owner">{ai.owner_name || 'Team'}</span>
                            <span className={`badge ${ai.status === 'done' ? 'badge-green' : ai.status === 'in_progress' ? 'badge-amber' : 'badge-gray'}`}>
                              {ai.status}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Actions */}
                  <div className="mc-actions">
                    {m.status === 'scheduled' && (
                      <>
                        <button className="btn btn-ghost btn-sm" onClick={() => sendReminder(m.id)}>⏰ Send Reminder</button>
                        <button className="btn btn-danger btn-sm" onClick={() => cancel(m.id)}>❌ Cancel</button>
                      </>
                    )}
                    {m.status === 'completed' && (
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => generateMom(m.id)}
                        disabled={generatingMom === m.id}
                        id={`gen-mom-${m.id}`}
                      >
                        {generatingMom === m.id ? <><span className="spinner" /> Generating...</> : '📄 Generate & Send MoM'}
                      </button>
                    )}
                    {m.ics_path && (
                      <span className="badge badge-cyan">📎 .ics saved</span>
                    )}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
