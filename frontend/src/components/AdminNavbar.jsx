import { NavLink, useNavigate } from 'react-router-dom'
import { useAdminAuth } from '../context/AdminAuthContext'

export default function AdminNavbar() {
  const { admin, logout } = useAdminAuth()
  const navigate = useNavigate()

  return (
    <div className="navbar">
      <div className="navbar-inner">
        <div className="auth-logo" style={{ marginBottom: 0 }}>
          <div className="mark" style={{ background: 'linear-gradient(135deg, #ff9142, #ff4d6a)' }}>FS</div>
          <div>
            <span className="name">FinShield</span>
            <span className="tag">Fraud Monitoring Console</span>
          </div>
        </div>
        <div className="nav-links">
          <NavLink to="/admin/dashboard" className={({isActive}) => isActive ? 'active' : ''}>Overview</NavLink>
          <NavLink to="/admin/transactions" className={({isActive}) => isActive ? 'active' : ''}>Transactions</NavLink>
          <NavLink to="/admin/alerts" className={({isActive}) => isActive ? 'active' : ''}>Fraud Alerts</NavLink>
          <NavLink to="/admin/beneficiaries" className={({isActive}) => isActive ? 'active' : ''}>Beneficiaries</NavLink>
          <NavLink to="/admin/audit-logs" className={({isActive}) => isActive ? 'active' : ''}>Audit Logs</NavLink>
        </div>
        <div className="nav-right">
          <span className="text-secondary" style={{ fontSize: 13 }}>{admin?.name}</span>
          <button className="btn btn-secondary btn-sm" onClick={() => { logout(); navigate('/admin/login') }}>
            Log out
          </button>
        </div>
      </div>
    </div>
  )
}
