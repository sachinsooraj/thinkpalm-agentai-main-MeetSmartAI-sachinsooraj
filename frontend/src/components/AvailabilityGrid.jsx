import { format } from 'date-fns'
import './AvailabilityGrid.css'

export default function AvailabilityGrid({ slots, onSelectSlot, selectedSlot, participantCount }) {
  if (slots.length === 0) {
    return (
      <div className="grid-empty card">
        <div className="grid-empty-icon">📅</div>
        <h3>Availability Grid</h3>
        <p>Select participants and click "Find Common Availability" to see open slots here.</p>
      </div>
    )
  }

  // Group slots by date
  const byDate = {}
  for (const slot of slots) {
    const key = format(new Date(slot.start_time), 'yyyy-MM-dd')
    if (!byDate[key]) byDate[key] = []
    byDate[key].push(slot)
  }

  const isSelected = (slot) =>
    selectedSlot &&
    slot.start_time === selectedSlot.start_time

  return (
    <div className="availability-grid card animate-in">
      <div className="grid-header">
        <h3>Common Availability</h3>
        <span className="badge badge-green">{slots.length} slots · {participantCount} participants</span>
      </div>

      <div className="grid-legend">
        <span className="legend-dot legend-free" /> Free for all
        <span className="legend-dot legend-selected" style={{ marginLeft: 16 }} /> Selected
      </div>

      <div className="date-groups">
        {Object.entries(byDate).map(([date, daySlots]) => (
          <div key={date} className="date-group">
            <div className="date-label">
              {format(new Date(date + 'T00:00:00'), 'EEEE, d MMMM')}
              <span className="badge badge-gray" style={{ marginLeft: 8, fontSize: '0.7rem' }}>
                {daySlots.length} slot{daySlots.length !== 1 ? 's' : ''}
              </span>
            </div>
            <div className="slots-row">
              {daySlots.map((slot, i) => (
                <button
                  key={i}
                  id={`slot-${date}-${i}`}
                  className={`slot-btn ${isSelected(slot) ? 'slot-selected' : 'slot-free'}`}
                  onClick={() => onSelectSlot(slot)}
                  title={`${format(new Date(slot.start_time), 'hh:mm a')} — ${format(new Date(slot.end_time), 'hh:mm a')}\nAll ${participantCount} participants free`}
                >
                  <span className="slot-time">{format(new Date(slot.start_time), 'hh:mm a')}</span>
                  <span className="slot-duration">
                    {Math.round((new Date(slot.end_time) - new Date(slot.start_time)) / 60000)}m
                  </span>
                  {isSelected(slot) && <span className="slot-check">✓</span>}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
