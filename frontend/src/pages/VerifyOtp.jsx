import { useState } from 'react'
import { useLocation, useNavigate, Link } from 'react-router-dom'
import { api, apiErrorMessage } from '../services/api'

export default function VerifyOtp() {
  const location = useLocation()
  const navigate = useNavigate()
  const state = location.state || {}
  const [code, setCode] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)

  if (!state.transaction_id) {
    return (
      <div className="page">
        <div className="container" style={{ maxWidth: 480 }}>
          <div className="card empty-state">
            No pending OTP challenge found. <Link to="/transfer">Start a new transfer</Link>.
          </div>
        </div>
      </div>
    )
  }

  const submit = async (e) => {
    e.preventDefault()
    setError(''); setLoading(true)
    try {
      const res = await api.post('/api/transactions/verify/otp', {
        transaction_id: state.transaction_id,
        otp_code: code,
      })
      if (res.data.success) {
        setSuccess(res.data.message)
        setTimeout(() => navigate('/history'), 1200)
      } else {
        setError(res.data.message)
      }
    } catch (err) {
      setError(apiErrorMessage(err, 'Verification failed.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page">
      <div className="container" style={{ maxWidth: 480 }}>
        <div className="card">
          <div className="verify-icon medium">🔐</div>
          <h1 style={{ fontSize: 19, margin: '0 0 6px' }}>Verify this transaction</h1>
          <p className="text-secondary" style={{ fontSize: 14, marginBottom: 4 }}>
            We noticed something slightly unusual about this transfer. Enter the
            one-time code we sent to your registered phone number to continue.
          </p>
          <p className="mono text-muted" style={{ fontSize: 12 }}>Ref: {state.reference}</p>

          {state.demo_otp_code && (
            <div className="auth-info">
              <b>Demo mode:</b> no real SMS is sent in this hackathon build. Your OTP is <b className="mono">{state.demo_otp_code}</b>.
            </div>
          )}
          {error && <div className="auth-error">{error}</div>}
          {success && <div className="auth-info" style={{ background: 'var(--low-bg)', color: 'var(--low)' }}>{success}</div>}

          <form onSubmit={submit}>
            <div className="field">
              <label>6-digit code</label>
              <input
                value={code} onChange={e => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                maxLength={6} inputMode="numeric" placeholder="••••••"
                style={{ fontFamily: 'var(--mono)', fontSize: 20, letterSpacing: 6, textAlign: 'center' }}
                required
              />
            </div>
            <button className="btn btn-primary" disabled={loading || code.length !== 6}>
              {loading ? 'Verifying…' : 'Confirm transaction'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
