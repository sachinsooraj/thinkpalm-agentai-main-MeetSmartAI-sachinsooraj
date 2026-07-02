import { useState, useEffect } from 'react'
import axios from 'axios'
import toast from 'react-hot-toast'
import './NotesUpload.css'

const API = '/api'

const SAMPLE_TRANSCRIPT = `Meeting: Q3 Roadmap Planning
Date: June 20, 2026
Attendees: Priya Nair, Arjun Sharma, Sanjay Pillai, Divya Krishnan

Priya opened the meeting and reviewed Q2 metrics. The team achieved 85% of planned milestones.

Key Discussion:
- The AI feature rollout was delayed due to API integration issues. Decided to prioritize this in Q3.
- Divya presented the new UX wireframes. The team agreed to proceed with the dark mode redesign.
- Rahul flagged that the staging environment needs to be set up before development begins.

Decisions:
- Agreed to start AI feature development in Week 1 of Q3 with Arjun's team.
- Design sprint scheduled for June 28 to July 5.
- Weekly syncs confirmed every Tuesday at 10 AM IST.

Action items:
- Arjun Sharma will set up the Q3 project board in Jira by June 22. Urgent.
- Divya Krishnan needs to complete UX wireframes by July 5.
- Rahul Menon should configure staging server by June 25.
- Priya Nair to draft Q3 OKRs document by June 24.
- Sanjay will share Q2 retrospective notes with the team by June 21.

Next meeting: Tuesday June 24, 10 AM IST.`

export default function NotesUpload() {
  const [meetings, setMeetings] = useState([])
  const [selectedMeeting, setSelectedMeeting] = useState('')
  const [transcript, setTranscript] = useState('')
  const [processing, setProcessing] = useState(false)
  const [result, setResult] = useState(null)
  const [activeTab, setActiveTab] = useState('summary')

  useEffect(() => {
    axios.get(`${API}/meetings/`)
      .then(r => setMeetings(r.data))
      .catch(() => {})
  }, [])

  const process = async () => {
    if (!selectedMeeting) return toast.error('Select a meeting')
    if (!transcript.trim()) return toast.error('Paste meeting notes or transcript')
    setProcessing(true)
    setResult(null)
    try {
      const res = await axios.post(`${API}/notes/process`, {
        meeting_id: parseInt(selectedMeeting),
        transcript,
      })
      setResult(res.data)
      toast.success('Notes processed successfully!')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Processing failed')
    } finally {
      setProcessing(false)
    }
  }

  const generateMom = async () => {
    if (!selectedMeeting) return
    try {
      await axios.post(`${API}/notes/generate-mom/${selectedMeeting}`)
      toast.success('📄 MoM generated and emailed! Check /outputs folder.')
    } catch {
      toast.error('MoM generation failed')
    }
  }

  const PRIORITY_COLORS = { high: 'badge-red', medium: 'badge-amber', low: 'badge-green' }

  return (
    <div className="notes-page">
      <div className="page-header">
        <h1>Notes & MoM Generator</h1>
        <p>Paste a meeting transcript and let AI extract structured notes, decisions, and action items.</p>
      </div>

      <div className="notes-layout">
        {/* Left: Input */}
        <div className="notes-input-panel">
          <div className="card">
            <h3>Meeting Transcript</h3>

            <div className="form-group mt-4">
              <label>Select Meeting</label>
              <select
                id="notes-meeting-select"
                value={selectedMeeting}
                onChange={e => setSelectedMeeting(e.target.value)}
              >
                <option value="">Choose a meeting...</option>
                {meetings.map(m => (
                  <option key={m.id} value={m.id}>
                    [{m.status}] {m.title}
                  </option>
                ))}
              </select>
            </div>

            <div className="form-group mt-4">
              <label>Transcript / Notes</label>
              <textarea
                id="transcript-input"
                value={transcript}
                onChange={e => setTranscript(e.target.value)}
                placeholder="Paste your meeting transcript or notes here..."
                rows={16}
              />
            </div>

            <div className="notes-input-actions mt-4">
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => setTranscript(SAMPLE_TRANSCRIPT)}
                id="load-sample-btn"
              >
                Load Sample
              </button>
              <button
                id="process-notes-btn"
                className="btn btn-primary"
                onClick={process}
                disabled={processing}
              >
                {processing
                  ? <><span className="spinner" /> Processing with AI...</>
                  : '🧠 Process Notes'
                }
              </button>
            </div>

            {result && (
              <div className="mode-badge mt-4">
                <span className={`badge ${result.mode === 'rule-based' ? 'badge-amber' : 'badge-purple'}`}>
                  {result.mode === 'rule-based' ? '⚡ Rule-Based Mode' : '🤖 Gemini AI Mode'}
                </span>
                <span className="text-sm text-muted" style={{ marginLeft: 8 }}>
                  {result.action_items.length} actions · {result.decisions.length} decisions
                </span>
              </div>
            )}
          </div>
        </div>

        {/* Right: Results */}
        <div className="notes-result-panel">
          {!result ? (
            <div className="result-empty card">
              <div style={{ fontSize: '3rem', opacity: 0.3, marginBottom: 12 }}>🧠</div>
              <h3>AI Analysis</h3>
              <p>Paste transcript and click "Process Notes" to see structured output here.</p>
            </div>
          ) : (
            <div className="result-card card animate-in">
              <div className="result-header">
                <h3>{result.meeting_title}</h3>
                <button
                  id="generate-mom-btn"
                  className="btn btn-primary btn-sm"
                  onClick={generateMom}
                >
                  📄 Generate & Send MoM
                </button>
              </div>

              {/* Tabs */}
              <div className="result-tabs">
                {['summary', 'decisions', 'actions', 'topics'].map(tab => (
                  <button
                    key={tab}
                    className={`result-tab ${activeTab === tab ? 'active' : ''}`}
                    onClick={() => setActiveTab(tab)}
                  >
                    {{
                      summary: '📋 Summary',
                      decisions: '✅ Decisions',
                      actions: '📌 Action Items',
                      topics: '🏷 Topics',
                    }[tab]}
                  </button>
                ))}
              </div>

              <div className="result-body">
                {activeTab === 'summary' && (
                  <div className="summary-text">{result.summary}</div>
                )}

                {activeTab === 'decisions' && (
                  <div className="decisions-list">
                    {result.decisions.length === 0 ? (
                      <p className="text-muted">No decisions detected.</p>
                    ) : result.decisions.map((d, i) => (
                      <div key={i} className="decision-item">
                        <span className="decision-num">{i + 1}</span>
                        <span>{d}</span>
                      </div>
                    ))}
                  </div>
                )}

                {activeTab === 'actions' && (
                  <div className="ai-actions-list">
                    {result.action_items.length === 0 ? (
                      <p className="text-muted">No action items detected.</p>
                    ) : result.action_items.map((item, i) => (
                      <div key={i} className="ai-action-item">
                        <div className="ai-action-header">
                          <span className={`badge ${PRIORITY_COLORS[item.priority] || 'badge-gray'}`}>
                            {item.priority}
                          </span>
                          <span className="action-owner-chip">👤 {item.owner}</span>
                          <span className="action-deadline">📅 {item.deadline || 'TBD'}</span>
                        </div>
                        <div className="ai-action-desc">{item.description}</div>
                      </div>
                    ))}
                  </div>
                )}

                {activeTab === 'topics' && (
                  <div className="topics-cloud">
                    {result.key_topics.length === 0 ? (
                      <p className="text-muted">No key topics identified.</p>
                    ) : result.key_topics.map((t, i) => (
                      <span key={i} className="topic-chip badge badge-purple">{t}</span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
