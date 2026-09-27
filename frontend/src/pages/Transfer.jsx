import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, apiErrorMessage } from '../services/api'
import { getDeviceFingerprint, resetDeviceFingerprint, detectBrowser, detectOS } from '../services/device'
import RiskBadge from '../components/RiskBadge'

const SCENARIOS = [
  {
    key: 'A', label: 'Scenario A · Normal transfer', expect: 'LOW',
    recipient_account_number: '1011112222', recipient_name: 'Chinedu Okafor', amount: '20000',
    resetDevice: false, city: 'Lagos', simulated_hour: '',
    note: 'Known recipient, known device, normal amount & city.',
  },
  {
    key: 'B', label: 'Scenario B · New recipient', expect: 'MEDIUM',
    recipient_account_number: '1033334444', recipient_name: 'Tunde Bakare', amount: '90000',
    resetDevice: false, city: 'Lagos', simulated_hour: '',
    note: 'New recipient + amount moderately above average → OTP required.',
  },
  {
    key: 'C', label: 'Scenario C · New device + location', expect: 'HIGH',
    recipient_account_number: '1022223333', recipient_name: 'Amaka Eze', amount: '70000',
    resetDevice: true, city: 'Kano', simulated_hour: '',
    note: 'Known recipient, but new device + unusual city + raised amount → identity verification.',
  },
  {
    key: 'D', label: 'Scenario D · Multiple severe anomalies', expect: 'CRITICAL',
    recipient_account_number: '1099998888', recipient_name: 'Unknown Wallet Services', amount: '600000',
    resetDevice: true, city: 'Kano', simulated_hour: '3',
    note: 'New recipient, new device, unusual city, 3AM, extreme amount → blocked + fraud alert.',
  },
]

export default function Transfer() {
  const [form, setForm] = useState({
    recipient_account_number: '', recipient_name: '', amount: '', narration: '',
    city: 'Lagos', simulated_hour: '',
  })
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const navigate = useNavigate()

  const applyScenario = (s) => {
    setError(''); setResult(null)
    if (s.resetDevice) resetDeviceFingerprint()
    setForm({
      recipient_account_number: s.recipient_account_number,
      recipient_name: s.recipient_name,
      amount: s.amount,
      narration: `Demo ${s.key}`,
      city: s.city,
      simulated_hour: s.simulated_hour,
    })
  }

  const update = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    setError(''); setResult(null); setLoading(true)
    try {
      const payload = {
        recipient_account_number: form.recipient_account_number,
        recipient_name: form.recipient_name || undefined,
        amount: parseFloat(form.amount),
        narration: form.narration || undefined,
        device_fingerprint: getDeviceFingerprint(),
        browser: detectBrowser(),
        operating_system: detectOS(),
        city: form.city,
        country: 'Nigeria',
        simulated_hour: form.simulated_hour === '' ? undefined : parseInt(form.simulated_hour, 10),
      }
      const res = await api.post('/api/transactions', payload)
      setResult(res.data)

      if (res.data.requires_otp) {
        setTimeout(() => navigate('/verify/otp', { state: { ...res.data } }), 900)
      } else if (res.data.requires_verification) {
        setTimeout(() => navigate('/verify/facial', { state: { ...res.data } }), 900)
      }
    } catch (err) {
      setError(apiErrorMessage(err, 'Transfer could not be processed.'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page">
      <div className="container" style={{ maxWidth: 640 }}>
        <div className="page-header">
          <h1>Send money</h1>
          <p>Every transfer is screened by FinShield before it completes.</p>
        </div>

        <div className="scenario-panel">
          <h3>🎬 Hackathon demo scenarios</h3>
          <p>Click a preset to autofill the form, then hit "Send transfer" to trigger it live.</p>
          <div className="scenario-buttons">
            {SCENARIOS.map(s => (
              <button key={s.key} type="button" className="scenario-btn" onClick={() => applyScenario(s)} title={s.note}>
                {s.label} <RiskBadge level={s.expect} />
              </button>
            ))}
          </div>
        </div>

        <div className="card">
          {error && <div className="auth-error">{error}</div>}

          {result && (
            <div className={result.status === 'blocked' ? 'auth-error' : result.status === 'completed' ? 'auth-info' : 'auth-info'}
                 style={result.status === 'completed' ? { background: 'var(--low-bg)', color: 'var(--low)', borderColor: 'transparent' } : {}}>
              <strong>{result.customer_message}</strong>
              {result.reference && <div className="mono text-muted" style={{ marginTop: 6, fontSize: 12 }}>Ref: {result.reference}</div>}
              {result.requires_otp && <div style={{ marginTop: 6, fontSize: 12 }}>Redirecting to OTP verification…</div>}
              {result.requires_verification && <div style={{ marginTop: 6, fontSize: 12 }}>Redirecting to identity verification…</div>}
            </div>
          )}

          <form onSubmit={submit}>
            <div className="field">
              <label>Recipient account number</label>
              <input value={form.recipient_account_number} onChange={update('recipient_account_number')} maxLength={10} required />
            </div>
            <div className="field">
              <label>Recipient name (optional)</label>
              <input value={form.recipient_name} onChange={update('recipient_name')} />
            </div>
            <div className="field">
              <label>Amount (₦)</label>
              <input type="number" min="1" step="0.01" value={form.amount} onChange={update('amount')} required />
            </div>
            <div className="field">
              <label>Narration (optional)</label>
              <input value={form.narration} onChange={update('narration')} />
            </div>
            <div className="grid grid-2">
              <div className="field">
                <label>Your current city (for demo overrides)</label>
                <input value={form.city} onChange={update('city')} />
              </div>
              <div className="field">
                <label>Simulate hour of day (0-23, optional)</label>
                <input type="number" min="0" max="23" value={form.simulated_hour} onChange={update('simulated_hour')} placeholder="Leave blank for now" />
              </div>
            </div>
            <button className="btn btn-primary" disabled={loading}>
              {loading ? 'Analysing transaction…' : 'Send transfer'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
