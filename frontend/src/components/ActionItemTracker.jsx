import { useState, useEffect } from 'react'
import axios from 'axios'
import toast from 'react-hot-toast'
import './ActionItemTracker.css'

const API = '/api'

const STATUS_OPTIONS = ['pending', 'in_progress', 'done']
const STATUS_BADGE = {
  pending:     'badge-gray',
  in_progress: 'badge-amber',
  done:        'badge-green',
}
const PRIORITY_BADGE = {
  high:   'badge-red',
  medium: 'badge-amber',
  low:    'badge-green',
}

export default function ActionItemTracker() {
  const [meetings, setMeetings] = useState([])
  const [selectedMeeting, setSelectedMeeting] = useState('all')
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(false)
  const [filterStatus, setFilterStatus] = useState('all')
  const [updating, setUpdating] = useState(null)

  useEffect(() => {
    axios.get(`${API}/meetings/`)
      .then(r => setMeetings(r.data))
      .catch(() => {})
  }, [])

  useEffect(() => {
    loadItems()
  }, [selectedMeeting])

  const loadItems = async () => {
    setLoading(true)
    try {
      if (selectedMeeting === 'all') {
        // Load items from all meetings
        const res = await axios.get(`${API}/meetings/`)
        const allItems = []
        for (const meeting of res.data) {
          const r = await axios.get(`${API}/meetings/${meeting.id}/action-items`)
          allItems.push(...r.data.map(item => ({ ...item, meeting_title: meeting.title })))
        }
        setItems(allItems)
      } else {
        const res = await axios.get(`${API}/meetings/${selectedMeeting}/action-items`)
        const meeting = meetings.find(m => m.id === parseInt(selectedMeeting))
        setItems(res.data.map(item => ({ ...item, meeting_title: meeting?.title || '' })))
      }
    } catch {
      toast.error('Failed to load action items')
    } finally {
      setLoading(false)
    }
  }

  const updateStatus = async (itemId, status) => {
    setUpdating(itemId)
    try {
      await axios.patch(`${API}/meetings/action-items/${itemId}/status`, { status })
      setItems(prev => prev.map(i => i.id === itemId ? { ...i, status } : i))
      toast.success(`Status updated to "${status}"`)
    } catch {
      toast.error('Update failed')
    } finally {
      setUpdating(null)
    }
  }

  const exportJSON = () => {
    const data = JSON.stringify(filteredItems, null, 2)
    const blob = new Blob([data], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `action_items_${new Date().toISOString().slice(0,10)}.json`
    a.click()
    toast.success('Action items exported as JSON')
  }

  const filteredItems = filterStatus === 'all'
    ? items
    : items.filter(i => i.status === filterStatus)

  const stats = {
    total:       items.length,
    pending:     items.filter(i => i.status === 'pending').length,
    in_progress: items.filter(i => i.status === 'in_progress').length,
    done:        items.filter(i => i.status === 'done').length,
  }

  return (
    <div className="tracker-page">
      <div className="page-header">
        <h1>Action Item Tracker</h1>
        <p>Track and update all meeting action items across ThinkPalm team.</p>
      </div>

      {/* Stats */}
      <div className="grid-4 mb-4">
        <div className="stat-card">
          <div className="stat-icon">📋</div>
          <div className="stat-value">{stats.total}</div>
          <div className="stat-label">Total Items</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">⏳</div>
          <div className="stat-value" style={{ color: 'var(--text-secondary)' }}>{stats.pending}</div>
          <div className="stat-label">Pending</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">🔄</div>
          <div className="stat-value" style={{ color: 'var(--amber-light)' }}>{stats.in_progress}</div>
          <div className="stat-label">In Progress</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon">✅</div>
          <div className="stat-value" style={{ color: '#34d399' }}>{stats.done}</div>
          <div className="stat-label">Done</div>
        </div>
      </div>

      {/* Controls */}
      <div className="tracker-controls card mb-4">
        <div className="form-group" style={{ flex: 1 }}>
          <label>Filter by Meeting</label>
          <select
            id="meeting-filter-select"
            value={selectedMeeting}
            onChange={e => setSelectedMeeting(e.target.value)}
          >
            <option value="all">All Meetings</option>
            {meetings.map(m => (
              <option key={m.id} value={m.id}>{m.title}</option>
            ))}
          </select>
        </div>
        <div className="filter-tabs" style={{ alignItems: 'flex-end' }}>
          {['all', 'pending', 'in_progress', 'done'].map(s => (
            <button
              key={s}
              className={`filter-tab ${filterStatus === s ? 'active' : ''}`}
              onClick={() => setFilterStatus(s)}
            >
              {s.replace('_', ' ')}
            </button>
          ))}
        </div>
        <button
          id="export-json-btn"
          className="btn btn-secondary btn-sm"
          onClick={exportJSON}
          disabled={filteredItems.length === 0}
          style={{ alignSelf: 'flex-end' }}
        >
          ⬇ Export JSON
        </button>
      </div>

      {/* Table */}
      {loading ? (
        <div className="loading-state">
          <div className="spinner" /><span className="text-muted">Loading action items...</span>
        </div>
      ) : filteredItems.length === 0 ? (
        <div className="card empty-state">
          <div style={{ fontSize: '2.5rem', opacity: 0.3, marginBottom: 12 }}>📭</div>
          <h3>No action items</h3>
          <p>Process meeting notes to generate action items.</p>
        </div>
      ) : (
        <div className="card tracker-table-wrap">
          <table className="tracker-table" id="action-items-table">
            <thead>
              <tr>
                <th>#</th>
                <th>Action Item</th>
                <th>Meeting</th>
                <th>Owner</th>
                <th>Deadline</th>
                <th>Priority</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredItems.map((item, idx) => (
                <tr key={item.id} className={`priority-row-${item.priority}`}>
                  <td className="td-num">{idx + 1}</td>
                  <td className="td-desc">{item.description}</td>
                  <td className="td-meeting">{item.meeting_title}</td>
                  <td className="td-owner">{item.owner_name || '—'}</td>
                  <td className="td-deadline">
                    {item.deadline
                      ? new Date(item.deadline).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })
                      : <span className="text-muted">TBD</span>
                    }
                  </td>
                  <td>
                    <span className={`badge ${PRIORITY_BADGE[item.priority] || 'badge-gray'}`}>
                      {item.priority}
                    </span>
                  </td>
                  <td>
                    <select
                      id={`status-${item.id}`}
                      className="status-select"
                      value={item.status}
                      onChange={e => updateStatus(item.id, e.target.value)}
                      disabled={updating === item.id}
                      style={{
                        borderColor: item.status === 'done' ? 'rgba(16,185,129,0.4)'
                          : item.status === 'in_progress' ? 'rgba(245,158,11,0.4)'
                          : 'var(--border)',
                      }}
                    >
                      {STATUS_OPTIONS.map(s => (
                        <option key={s} value={s}>{s.replace('_', ' ')}</option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
