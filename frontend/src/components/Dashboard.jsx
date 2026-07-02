import { useState, useEffect } from 'react'
import axios from 'axios'
import { format } from 'date-fns'
import toast from 'react-hot-toast'
import './Dashboard.css'

const API = '/api'

function StatCard({ icon, value, label, color }) {
  return (
    <div className="stat-card animate-in" style={{ '--accent': color }}>
      <div className="stat-icon">{icon}</div>
      <div className="stat-value" style={{ color }}>{value}</div>
      <div className="stat-label">{label}</div>
    </div>
  )
}

export default function Dashboard() {
  const [meetings, setMeetings] = useState([])
  const [employees, setEmployees] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const [mRes, eRes] = await Promise.all([
          axios.get(`${API}/meetings/`),
          axios.get(`${API}/availability/employees`),
        ])
        setMeetings(mRes.data)
        setEmployees(eRes.data)
      } catch {
        toast.error('Could not connect to backend. Is the server running?')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const now = new Date()
  const upcoming = meetings.filter(m => new Date(m.start_time) > now && m.status === 'scheduled')
  const completed = meetings.filter(m => m.status === 'completed')
  const cancelled = meetings.filter(m => m.status === 'cancelled')

  const nextMeeting = upcoming[0]

  return (
    <div className="dashboard">
      {/* Header */}
      <div className="page-header">
        <h1>Welcome to MeetSmart AI 🧠</h1>
        <p>AI-powered internal meeting platform for ThinkPalm teams</p>
      </div>

      {/* Stats */}
      <div className="grid-4 mb-4">
        <StatCard icon="📅" value={loading ? '—' : upcoming.length} label="Upcoming Meetings"  color="#a78bfa" />
        <StatCard icon="✅" value={loading ? '—' : completed.length} label="Completed"         color="#34d399" />
        <StatCard icon="👥" value={loading ? '—' : employees.length} label="Team Members"      color="#67e8f9" />
        <StatCard icon="❌" value={loading ? '—' : cancelled.length} label="Cancelled"         color="#fca5a5" />
      </div>

      <div className="dashboard-body">
        {/* Next meeting highlight */}
        {nextMeeting && (
          <div className="next-meeting-card card animate-in">
            <div className="next-meeting-header">
              <span className="badge badge-purple">⏰ Next Meeting</span>
              <span className={`badge badge-green`}>Scheduled</span>
            </div>
            <h2 className="next-meeting-title">{nextMeeting.title}</h2>
            <div className="next-meeting-meta">
              <span>🗓 {format(new Date(nextMeeting.start_time), 'EEEE, d MMMM yyyy')}</span>
              <span>🕐 {format(new Date(nextMeeting.start_time), 'hh:mm a')} — {format(new Date(nextMeeting.end_time), 'hh:mm a')}</span>
              <span>📍 {nextMeeting.location}</span>
            </div>
            <div className="next-meeting-participants">
              {nextMeeting.participants?.map(p => (
                <div key={p.id} className="participant-chip">
                  <span className="avatar avatar-sm" style={{ background: stringToColor(p.name) }}>
                    {p.avatar_initials || p.name[0]}
                  </span>
                  <span>{p.name}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Team roster */}
        <div className="card animate-in">
          <div className="section-title">Team Members</div>
          {loading ? (
            <div className="flex items-center gap-2"><div className="spinner" /><span className="text-muted text-sm">Loading...</span></div>
          ) : (
            <div className="team-grid">
              {employees.map(emp => (
                <div key={emp.id} className="team-card">
                  <span className="avatar avatar-lg" style={{ background: stringToColor(emp.name) }}>
                    {emp.avatar_initials || emp.name[0]}
                  </span>
                  <div className="team-info">
                    <div className="team-name">{emp.name}</div>
                    <div className="team-role">{emp.role}</div>
                    <span className="badge badge-cyan" style={{ marginTop: 4 }}>{emp.department}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Agent status */}
        <div className="card animate-in">
          <div className="section-title">AI Agents Status</div>
          <div className="agents-grid">
            {AGENTS.map(agent => (
              <div key={agent.name} className="agent-chip">
                <span className="agent-icon">{agent.icon}</span>
                <div>
                  <div className="agent-name">{agent.name}</div>
                  <div className="agent-desc">{agent.desc}</div>
                </div>
                <span className="badge badge-green">Active</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

const AGENTS = [
  { icon: '📡', name: 'Availability Agent', desc: 'Reads/writes schedule slots' },
  { icon: '🤝', name: 'Booking Agent',      desc: 'Optimal slot selection' },
  { icon: '📨', name: 'Invite Agent',       desc: 'Generates & sends .ics invites' },
  { icon: '📝', name: 'Notes Agent',        desc: 'AI transcript processing' },
  { icon: '📄', name: 'MoM Agent',          desc: 'Word doc generation & email' },
  { icon: '⏰', name: 'Reminder Agent',     desc: 'Pre/post-meeting follow-ups' },
]

function stringToColor(str) {
  const colors = ['#7c3aed','#059669','#0284c7','#b45309','#be185d','#4338ca','#0891b2','#15803d']
  let hash = 0
  for (let i = 0; i < str.length; i++) hash = str.charCodeAt(i) + ((hash << 5) - hash)
  return colors[Math.abs(hash) % colors.length]
}
