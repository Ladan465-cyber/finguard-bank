import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { adminApi, apiErrorMessage } from '../../services/api'
import { useAdminAuth } from '../../context/AdminAuthContext'

export default function AdminLogin() {
  const [email, setEmail] = useState('admin@finguard.ng')
  const [password, setPassword] = useState('Admin@123')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAdminAuth()
  const navigate = useNavigate()

  const submit = async (e) => {
    e.preventDefault()
    setError(''); setLoading(true)
    try {
      const res = await adminApi.post('/api/auth/admin/login', { email, password })
      login(res.data.access_token, res.data.full_name)
      navigate('/admin/dashboard')
    } catch (err) {
      setError(apiErrorMessage(err, 'Invalid admin credentials.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">
          <div className="mark" style={{ background: 'linear-gradient(135deg, #ff9142, #ff4d6a)' }}>FS</div>
          <div>
            <span className="name">FinShield Console</span>
            <span className="tag">Authorised personnel only</span>
          </div>
        </div>

        {error && <div className="auth-error">{error}</div>}

        <form onSubmit={submit}>
          <div className="field">
            <label>Admin email</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} required />
          </div>
          <div className="field">
            <label>Password</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} required />
          </div>
          <button className="btn btn-primary" disabled={loading}>
            {loading ? 'Signing in…' : 'Enter console'}
          </button>
        </form>

        <div className="auth-footer">
          <Link to="/login" style={{ color: 'var(--text-muted)' }}>← Back to customer login</Link>
        </div>

        <div className="demo-hint">
          <b>Demo admin login:</b> admin@finguard.ng / Admin@123
        </div>
      </div>
    </div>
  )
}
