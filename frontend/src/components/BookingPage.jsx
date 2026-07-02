import { useState, useEffect } from 'react'
import axios from 'axios'
import { format, addDays, parse, isValid } from 'date-fns'
import toast from 'react-hot-toast'
import AvailabilityGrid from './AvailabilityGrid.jsx'
import './BookingPage.css'

const API = '/api'

const TIME_OPTIONS = [
  '08:00', '08:30', '09:00', '09:30', '10:00', '10:30',
  '11:00', '11:30', '12:00', '12:30', '13:00', '13:30',
  '14:00', '14:30', '15:00', '15:30', '16:00', '16:30',
  '17:00', '17:30', '18:00',
]

function fmt12(time24) {
  const [h, m] = time24.split(':').map(Number)
  const ampm = h >= 12 ? 'PM' : 'AM'
  const hour = h % 12 || 12
  return `${hour}:${m.toString().padStart(2, '0')} ${ampm}`
}

function avatarColor(str) {
  const colors = ['#06C167','#0066cc','#e67e22','#8e44ad','#c0392b','#16a085','#d35400','#2980b9']
  let hash = 0
  for (let i = 0; i < str.length; i++) hash = str.charCodeAt(i) + ((hash << 5) - hash)
  return colors[Math.abs(hash) % colors.length]
}

export default function BookingPage() {
  const [employees, setEmployees]             = useState([])
  const [selectedParticipants, setSelected]  = useState([])
  const [organizer, setOrganizer]            = useState('')
  const [title, setTitle]                    = useState('')
  const [agenda, setAgenda]                  = useState('')
  const [duration, setDuration]              = useState(60)
  const [preferredDate, setPreferredDate]    = useState(format(new Date(), 'yyyy-MM-dd'))
  const [preferredTime, setPreferredTime]    = useState('')      // '' = auto-assign
  const [timeMode, setTimeMode]              = useState('auto')  // 'auto' | 'pick'
  const [location, setLocation]             = useState('Google Meet / Teams')
  const [overlapSlots, setOverlapSlots]      = useState([])
  const [selectedSlot, setSelectedSlot]      = useState(null)
  const [searching, setSearching]            = useState(false)
  const [booking, setBooking]               = useState(false)
  const [booked, setBooked]                 = useState(null)

  useEffect(() => {
    axios.get(`${API}/availability/employees`)
      .then(r => setEmployees(r.data))
      .catch(() => toast.error('Failed to load employees'))
  }, [])

  const toggleParticipant = (id) => {
    setSelected(prev => prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id])
    setOverlapSlots([])
    setSelectedSlot(null)
  }

  // Build a full ISO datetime from preferredDate + preferredTime if both set
  const buildManualStartTime = () => {
    if (!preferredDate || !preferredTime) return undefined
    return `${preferredDate}T${preferredTime}:00`
  }

  const findSlots = async () => {
    if (selectedParticipants.length < 1) return toast.error('Select at least one participant')
    setSearching(true)
    try {
      const allIds = organizer
        ? [...new Set([parseInt(organizer), ...selectedParticipants])]
        : selectedParticipants
      const today   = new Date()
      const endDate = addDays(today, 14)
      const res = await axios.post(`${API}/availability/overlap`, {
        employee_ids:     allIds,
        from_date:        preferredDate || format(today, 'yyyy-MM-dd'),
        to_date:          format(endDate, 'yyyy-MM-dd'),
        duration_minutes: duration,
      })
      setOverlapSlots(res.data)
      if (res.data.length === 0) {
        toast('No common slots in next 14 days — try fewer participants or a different date.', { icon: '⚠️' })
      } else {
        toast.success(`Found ${res.data.length} common slot(s)`)
      }
    } catch {
      toast.error('Failed to find availability')
    } finally {
      setSearching(false)
    }
  }

  const handleBook = async () => {
    if (!title.trim())                    return toast.error('Enter a meeting title')
    if (!organizer)                       return toast.error('Select an organizer')
    if (selectedParticipants.length < 1) return toast.error('Select at least one participant')
    if (timeMode === 'pick' && !preferredTime) return toast.error('Select a specific time or switch to Auto mode')

    // Determine start_time to send
    let startTime = undefined
    if (selectedSlot) {
      startTime = selectedSlot.start_time   // from grid
    } else if (timeMode === 'pick') {
      startTime = buildManualStartTime()    // from date+time picker
    }
    // if neither → backend auto-picks earliest slot

    setBooking(true)
    try {
      const payload = {
        title,
        agenda,
        organizer_id:     parseInt(organizer),
        participant_ids:  selectedParticipants,
        duration_minutes: duration,
        preferred_date:   preferredDate || undefined,
        start_time:       startTime,
        location,
      }
      const res = await axios.post(`${API}/booking/book`, payload)
      setBooked(res.data)
      toast.success('Meeting booked! Invites sent.')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Booking failed — no common slot found')
    } finally {
      setBooking(false)
    }
  }

  const reset = () => {
    setBooked(null); setTitle(''); setAgenda('')
    setSelected([]); setOrganizer(''); setOverlapSlots([])
    setSelectedSlot(null); setPreferredTime(''); setTimeMode('auto')
  }

  /* ── Success screen ─────────────────────────── */
  if (booked) {
    return (
      <div className="booking-success animate-in">
        <div className="success-check">✓</div>
        <h2>Meeting Booked</h2>
        <p>Calendar invites have been sent to all participants.</p>
        <div className="success-card card">
          <div className="success-title">{booked.title}</div>
          <div className="success-meta">
            <div className="meta-row">
              <span className="meta-icon">📅</span>
              <span>{format(new Date(booked.start_time), 'EEEE, d MMMM yyyy')}</span>
            </div>
            <div className="meta-row">
              <span className="meta-icon">🕐</span>
              <span>{format(new Date(booked.start_time), 'hh:mm a')} — {format(new Date(booked.end_time), 'hh:mm a')}</span>
            </div>
            <div className="meta-row">
              <span className="meta-icon">📍</span>
              <span>{booked.location}</span>
            </div>
          </div>
          <div className="success-participants">
            {booked.participants?.map(p => (
              <span key={p.id} className="p-chip">
                <span className="avatar avatar-sm" style={{ background: avatarColor(p.name) }}>{p.avatar_initials || p.name[0]}</span>
                {p.name}
              </span>
            ))}
          </div>
          <div className="success-actions">
            <button className="btn btn-accent" onClick={reset}>Book Another</button>
            <a className="btn btn-secondary" href="/meetings">View All Meetings</a>
          </div>
        </div>
      </div>
    )
  }

  /* ── Main form ──────────────────────────────── */
  const canBook = title.trim() && organizer && selectedParticipants.length > 0

  // What's the active time source?
  const activeTimeSource =
    selectedSlot ? 'grid'
    : timeMode === 'pick' && preferredTime ? 'manual'
    : 'auto'

  return (
    <div className="booking-page">
      <div className="page-header">
        <h1>Book a Meeting</h1>
        <p>Fill in the details, pick participants, then confirm.</p>
      </div>

      <div className="booking-layout">
        {/* ── Left: Form ── */}
        <div className="booking-form">

          {/* Step 1: Meeting Details */}
          <div className="step-section">
            <div className="step-label"><span className="step-num">1</span> Meeting Details</div>
            <div className="card step-card">

              <div className="form-group">
                <label>Meeting Title *</label>
                <input
                  id="meeting-title"
                  type="text"
                  placeholder="e.g. Q3 Roadmap Review"
                  value={title}
                  onChange={e => setTitle(e.target.value)}
                />
              </div>

              <div className="form-group mt-4">
                <label>Agenda</label>
                <textarea
                  id="meeting-agenda"
                  placeholder={"1. Review Q2 deliverables\n2. Q3 priorities\n3. Action items"}
                  value={agenda}
                  onChange={e => setAgenda(e.target.value)}
                  rows={3}
                />
              </div>

              {/* Date + Duration row */}
              <div className="grid-2 mt-4">
                <div className="form-group">
                  <label>Date</label>
                  <input
                    id="preferred-date"
                    type="date"
                    value={preferredDate}
                    onChange={e => { setPreferredDate(e.target.value); setSelectedSlot(null) }}
                  />
                </div>
                <div className="form-group">
                  <label>Duration</label>
                  <select id="meeting-duration" value={duration} onChange={e => setDuration(parseInt(e.target.value))}>
                    <option value={30}>30 min</option>
                    <option value={45}>45 min</option>
                    <option value={60}>1 hour</option>
                    <option value={90}>1.5 hours</option>
                    <option value={120}>2 hours</option>
                  </select>
                </div>
              </div>

              {/* Time picker section */}
              <div className="time-section mt-4">
                <div className="time-mode-header">
                  <label>Start Time</label>
                  <div className="time-mode-toggle">
                    <button
                      className={`tmt-btn ${timeMode === 'auto' ? 'active' : ''}`}
                      onClick={() => { setTimeMode('auto'); setPreferredTime(''); setSelectedSlot(null) }}
                    >Auto</button>
                    <button
                      className={`tmt-btn ${timeMode === 'pick' ? 'active' : ''}`}
                      onClick={() => { setTimeMode('pick'); setSelectedSlot(null) }}
                    >Pick time</button>
                  </div>
                </div>

                {timeMode === 'auto' ? (
                  <div className="time-auto-hint">
                    Time will be auto-assigned from available slots, or pick from the grid →
                  </div>
                ) : (
                  <div className="time-grid">
                    {TIME_OPTIONS.map(t => (
                      <button
                        key={t}
                        className={`time-btn ${preferredTime === t ? 'selected' : ''}`}
                        onClick={() => { setPreferredTime(t); setSelectedSlot(null) }}
                      >
                        {fmt12(t)}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <div className="form-group mt-4">
                <label>Location</label>
                <input
                  id="meeting-location"
                  type="text"
                  placeholder="Google Meet / Teams / Conference Room"
                  value={location}
                  onChange={e => setLocation(e.target.value)}
                />
              </div>
            </div>
          </div>

          {/* Step 2: Participants */}
          <div className="step-section">
            <div className="step-label"><span className="step-num">2</span> Participants</div>
            <div className="card step-card">
              <div className="form-group">
                <label>Organizer *</label>
                <select id="organizer-select" value={organizer} onChange={e => setOrganizer(e.target.value)}>
                  <option value="">Select organizer...</option>
                  {employees.map(e => (
                    <option key={e.id} value={e.id}>{e.name} — {e.role}</option>
                  ))}
                </select>
              </div>
              <div className="form-group mt-4">
                <label>Attendees (click to select)</label>
                <div className="participant-chips mt-2">
                  {employees.map(emp => (
                    <button
                      key={emp.id}
                      id={`participant-${emp.id}`}
                      className={`participant-toggle ${selectedParticipants.includes(emp.id) ? 'selected' : ''}`}
                      onClick={() => toggleParticipant(emp.id)}
                    >
                      <span className="avatar avatar-sm" style={{ background: avatarColor(emp.name) }}>
                        {emp.avatar_initials || emp.name[0]}
                      </span>
                      <div className="p-info">
                        <div className="p-name">{emp.name}</div>
                        <div className="p-role">{emp.role}</div>
                      </div>
                      <span className={`p-check ${selectedParticipants.includes(emp.id) ? 'visible' : ''}`}>✓</span>
                    </button>
                  ))}
                </div>
              </div>

              {selectedParticipants.length > 0 && timeMode === 'auto' && (
                <button
                  id="find-slots-btn"
                  className="btn btn-secondary w-full mt-4"
                  onClick={findSlots}
                  disabled={searching}
                >
                  {searching ? <><span className="spinner" />Searching...</> : '🔍 Find Common Availability'}
                </button>
              )}
            </div>
          </div>

          {/* Step 3: Confirm */}
          {canBook && (
            <div className="step-section animate-in">
              <div className="step-label"><span className="step-num">3</span> Confirm &amp; Book</div>
              <div className="card step-card confirm-card">

                {/* Show what time will be used */}
                {activeTimeSource === 'grid' && (
                  <div className="slot-chosen">
                    <div className="slot-chosen-label">Selected from grid</div>
                    <div className="slot-chosen-time">
                      {format(new Date(selectedSlot.start_time), 'EEEE, d MMMM')}
                      &nbsp;·&nbsp;
                      {format(new Date(selectedSlot.start_time), 'hh:mm a')} – {format(new Date(selectedSlot.end_time), 'hh:mm a')}
                    </div>
                    <button className="btn-link" onClick={() => setSelectedSlot(null)}>Clear selection</button>
                  </div>
                )}

                {activeTimeSource === 'manual' && (
                  <div className="slot-chosen">
                    <div className="slot-chosen-label">Specific time selected</div>
                    <div className="slot-chosen-time">
                      {preferredDate ? format(new Date(preferredDate), 'EEEE, d MMMM') : 'Today'}
                      &nbsp;·&nbsp;
                      {fmt12(preferredTime)} ({duration} min)
                    </div>
                    <button className="btn-link" onClick={() => setPreferredTime('')}>Clear time</button>
                  </div>
                )}

                {activeTimeSource === 'auto' && (
                  <p className="hint-text">
                    {overlapSlots.length > 0
                      ? '← Pick a slot from the grid, or confirm to auto-assign the earliest.'
                      : 'Confirming will auto-assign the earliest available slot for all participants.'}
                  </p>
                )}

                <button
                  id="book-meeting-btn"
                  className="btn btn-accent btn-lg w-full mt-4"
                  onClick={handleBook}
                  disabled={booking}
                >
                  {booking
                    ? <><span className="spinner" />Booking...</>
                    : '✓ Confirm & Book Meeting'
                  }
                </button>
              </div>
            </div>
          )}
        </div>

        {/* ── Right: Availability Grid ── */}
        <div className="booking-grid-panel">
          <AvailabilityGrid
            slots={overlapSlots}
            onSelectSlot={(slot) => { setSelectedSlot(slot); setTimeMode('auto'); setPreferredTime('') }}
            selectedSlot={selectedSlot}
            participantCount={[...new Set([parseInt(organizer) || 0, ...selectedParticipants])].filter(Boolean).length}
          />
        </div>
      </div>
    </div>
  )
}
