import { NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Navbar() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const initials = (user?.full_name || '?').split(' ').map(n => n[0]).slice(0, 2).join('')

  return (
    <div className="navbar">
      <div className="navbar-inner">
        <div className="auth-logo" style={{ marginBottom: 0 }}>
          <div className="mark">FG</div>
          <div>
            <span className="name">FinGuard</span>
            <span className="tag">Secure Banking. Intelligent Protection.</span>
          </div>
        </div>
        <div className="nav-links">
          <NavLink to="/dashboard" className={({isActive}) => isActive ? 'active' : ''}>Dashboard</NavLink>
          <NavLink to="/transfer" className={({isActive}) => isActive ? 'active' : ''}>Transfer</NavLink>
          <NavLink to="/history" className={({isActive}) => isActive ? 'active' : ''}>History</NavLink>
          <NavLink to="/devices" className={({isActive}) => isActive ? 'active' : ''}>Security</NavLink>
        </div>
        <div className="nav-right">
          <div className="nav-avatar">{initials}</div>
          <button className="btn btn-secondary btn-sm" onClick={() => { logout(); navigate('/login') }}>
            Log out
          </button>
        </div>
      </div>
    </div>
  )
}
