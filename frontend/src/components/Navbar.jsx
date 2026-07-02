import { NavLink } from 'react-router-dom'
import './Navbar.css'

const NAV_ITEMS = [
  { to: '/',         label: 'Dashboard',    icon: '🏠' },
  { to: '/book',     label: 'Book Meeting', icon: '📅' },
  { to: '/meetings', label: 'Meetings',     icon: '📋' },
  { to: '/notes',    label: 'Notes & MoM',  icon: '📝' },
  { to: '/actions',  label: 'Action Items', icon: '✅' },
]

export default function Navbar() {
  return (
    <header className="navbar">
      <div className="navbar-inner">
        {/* Brand */}
        <NavLink to="/" className="brand">
          <span className="brand-icon">🧠</span>
          <div>
            <div className="brand-name">MeetSmart AI</div>
            <div className="brand-sub">ThinkPalm Internal</div>
          </div>
        </NavLink>

        {/* Nav links */}
        <nav className="nav-links">
          {NAV_ITEMS.map(item => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `nav-item ${isActive ? 'nav-item--active' : ''}`
              }
            >
              <span>{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* Right badge */}
        <div className="navbar-badge">
          <span className="dot-pulse" />
          <span>Live</span>
        </div>
      </div>
    </header>
  )
}
