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
  const [showOtpModal, setShowOtpModal] = useState(!!state.demo_otp_code)

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

      if (res.data.success && res.data.requires_further_verification) {
        setSuccess(res.data.message)
        setTimeout(() => navigate('/verify/facial', {
          state: { transaction_id: res.data.transaction_id, reference: res.data.reference },
        }), 1000)
      } else if (res.data.success) {
        setSuccess(res.data.message)
        setTimeout(() => navigate(`/receipt/${state.transaction_id}`), 1200)
      } else {
  setError(res.data.message)
  setCode('')
}
    } catch (err) {
      setError(apiErrorMessage(err, 'Verification failed.'))
    } finally {
      setLoading(false)
    }
  }

  const autofillDemoCode = () => {
    setCode(state.demo_otp_code)
    setShowOtpModal(false)
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

          {state.demo_otp_code && (
            <button
              type="button"
              className="btn btn-secondary"
              style={{ marginTop: 10, fontSize: 12.5 }}
              onClick={() => setShowOtpModal(true)}
            >
              Show demo OTP code again
            </button>
          )}
        </div>
      </div>

      {showOtpModal && state.demo_otp_code && (
        <div className="modal-backdrop" onClick={() => setShowOtpModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 380, textAlign: 'center' }}>
            <div className="verify-icon medium" style={{ margin: '0 auto 16px' }}>📱</div>
            <h2 style={{ fontSize: 17, margin: '0 0 6px' }}>Demo mode: SMS simulation</h2>
            <p className="text-secondary" style={{ fontSize: 13.5, lineHeight: 1.6, marginBottom: 16 }}>
              No real SMS is sent in this hackathon build. Here's the one-time
              code that would normally arrive by text:
            </p>
            <div
              className="mono"
              style={{
                fontSize: 32, fontWeight: 700, letterSpacing: 8,
                background: 'var(--bg-elevated)', border: '1px solid var(--border-light)',
                borderRadius: 'var(--radius-sm)', padding: '14px 10px', marginBottom: 18,
                color: 'var(--accent)',
              }}
            >
              {state.demo_otp_code}
            </div>
            <div style={{ display: 'flex', gap: 10 }}>
              <button className="btn btn-secondary" onClick={() => setShowOtpModal(false)}>Close</button>
              <button className="btn btn-primary" onClick={autofillDemoCode}>Use this code</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}