import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, apiErrorMessage } from '../services/api'
import { useAuth } from '../context/AuthContext'

export default function Register() {
  const [form, setForm] = useState({
    full_name: '', email: '', phone: '', password: '', home_city: 'Lagos',
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const update = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const res = await api.post('/api/auth/register', form)
      login(res.data.access_token, res.data.full_name, res.data.user_id)
      navigate('/dashboard')
    } catch (err) {
      setError(apiErrorMessage(err, 'Registration failed.'))
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
        <div className="auth-info">
          New accounts start with ₦50,000 and no transaction history — so
          the fraud engine will initially judge only by absolute amount
          until a behaviour baseline builds up. For a full demo with rich
          history already in place, use the demo login on the sign-in page.
        </div>

        <form onSubmit={submit}>
          <div className="field">
            <label>Full name</label>
            <input value={form.full_name} onChange={update('full_name')} required />
          </div>
          <div className="field">
            <label>Email address</label>
            <input type="email" value={form.email} onChange={update('email')} required />
          </div>
          <div className="field">
            <label>Phone number</label>
            <input value={form.phone} onChange={update('phone')} placeholder="+2348012345678" required />
          </div>
          <div className="field">
            <label>City</label>
            <input value={form.home_city} onChange={update('home_city')} required />
          </div>
          <div className="field">
            <label>Password</label>
            <input type="password" value={form.password} onChange={update('password')} required minLength={6} />
          </div>
          <button className="btn btn-primary" disabled={loading}>
            {loading ? 'Creating account…' : 'Create account'}
          </button>
        </form>

        <div className="auth-footer">
          Already have an account? <Link to="/login">Sign in</Link>
        </div>
      </div>
    </div>
  )
}
