import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, apiErrorMessage } from '../services/api'
import { getDeviceFingerprint, detectBrowser, detectOS } from '../services/device'
import { useAuth } from '../context/AuthContext'

export default function Login() {
  const [email, setEmail] = useState('ngozi.chukwu@example.com')
  const [password, setPassword] = useState('Demo@123')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await api.post('/api/auth/login', {
        email, password,
        device_fingerprint: getDeviceFingerprint(),
        browser: detectBrowser(),
        operating_system: detectOS(),
        city: 'Lagos',
        country: 'Nigeria',
      })
      login(res.data.access_token, res.data.full_name, res.data.user_id)
      navigate('/dashboard')
    } catch (err) {
      setError(apiErrorMessage(err, 'Login failed. Check your credentials.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-logo">
          <div className="mark">FG</div>
          <div>
            <span className="name">FinGuard Bank</span>
            <span className="tag">Secure Banking. Intelligent Protection.</span>
          </div>
        </div>

        {error && <div className="auth-error">{error}</div>}

        <form onSubmit={submit}>
          <div className="field">
            <label>Email address</label>
            <input type="email" value={email} onChange={e => setEmail(e.target.value)} required />
          </div>
          <div className="field">
            <label>Password</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} required />
          </div>
          <button className="btn btn-primary" disabled={loading}>
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <div className="auth-footer">
          New to FinGuard? <Link to="/register">Create an account</Link>
          <br /><br />
          <Link to="/admin/login" style={{ color: 'var(--text-muted)' }}>Admin console →</Link>
        </div>

        <div className="demo-hint">
          <b>Demo login:</b> ngozi.chukwu@example.com / Demo@123<br />
          This account has 18 days of realistic transaction history already
          loaded, so the fraud engine has a genuine behaviour baseline to
          compare new transactions against.
        </div>
      </div>
    </div>
  )
}
