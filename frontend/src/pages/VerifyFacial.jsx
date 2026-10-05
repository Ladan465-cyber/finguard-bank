import { useState } from 'react'
import { useLocation, useNavigate, Link } from 'react-router-dom'
import { api, apiErrorMessage } from '../services/api'
import FaceCapture from '../components/FaceCapture'

export default function VerifyFacial() {
  const location = useLocation()
  const navigate = useNavigate()
  const state = location.state || {}
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [loading, setLoading] = useState(false)

  if (!state.transaction_id) {
    return (
      <div className="page">
        <div className="container" style={{ maxWidth: 480 }}>
          <div className="card empty-state">
            No pending identity check found. <Link to="/transfer">Start a new transfer</Link>.
          </div>
        </div>
      </div>
    )
  }

  const handleDescriptor = async (descriptor) => {
    setError(''); setLoading(true)
    try {
      const res = await api.post('/api/transactions/verify/facial', {
        transaction_id: state.transaction_id,
        descriptor,
      })
      if (res.data.success) {
        setSuccess(res.data.message)
        setTimeout(() => navigate(`/receipt/${state.transaction_id}`), 1200)
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
          <div className="verify-icon high">🛡️</div>
          <h1 style={{ fontSize: 19, margin: '0 0 6px' }}>Identity verification required</h1>
          <p className="text-secondary" style={{ fontSize: 14, marginBottom: 4 }}>
            For your security, this transaction needs a live face match
            before it can be completed.
          </p>
          <p className="mono text-muted" style={{ fontSize: 12, marginBottom: 16 }}>Ref: {state.reference}</p>

          {error && <div className="auth-error">{error}</div>}
          {success && <div className="auth-info" style={{ background: 'var(--low-bg)', color: 'var(--low)' }}>{success}</div>}

          {!success && (
            <FaceCapture
              buttonLabel={loading ? 'Verifying…' : 'Verify my identity'}
              helperText="Look directly at the camera in good lighting. Your live face is compared against the one captured when you set up Face ID — no photo is stored or sent, only the match result."
              onDescriptor={handleDescriptor}
            />
          )}

          <div className="auth-info" style={{ marginTop: 14 }}>
            Haven't set up Face ID yet? <Link to="/devices">Enroll your face</Link> from the Security page first, then come back here.
          </div>
        </div>
      </div>
    </div>
  )
}