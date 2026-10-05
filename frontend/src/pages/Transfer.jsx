import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, apiErrorMessage } from '../services/api'
import { getDeviceFingerprint, resetDeviceFingerprint, detectBrowser, detectOS } from '../services/device'
import RiskBadge from '../components/RiskBadge'

const SCENARIOS = [
  {
    key: '1', label: 'Scenario 1 · Normal transfer', expect: 'SAFE',
    recipient_account_number: '1011112222', recipient_name: 'Chinedu Okafor', amount: '20000',
    resetDevice: false, city: 'Lagos', simulated_hour: '',
    note: 'Known recipient, known device, normal amount, normal city -> approved instantly.',
  },
  {
    key: '2', label: 'Scenario 2 · New beneficiary, large amount', expect: 'VERIFY',
    recipient_account_number: '1033334444', recipient_name: 'Tunde Bakare', amount: '150000',
    resetDevice: false, city: 'Lagos', simulated_hour: '',
    note: 'Known device, but a large amount to a brand-new recipient -> OTP required.',
  },
  {
    key: '3', label: 'Scenario 3 · Ponzi-tagged recipient', expect: 'HIGH_RISK',
    recipient_account_number: '1099998888', recipient_name: 'Unknown Wallet Services', amount: '20000',
    resetDevice: false, city: 'Lagos', simulated_hour: '',
    note: 'Recipient is on the fraud watchlist -> warning modal appears before submit.',
  },
  {
    key: '4', label: 'Scenario 4 · New device + risky recipient', expect: 'HIGH_RISK',
    recipient_account_number: '1099998888', recipient_name: 'Unknown Wallet Services', amount: '40000',
    resetDevice: true, city: 'Kano', simulated_hour: '',
    note: 'New device, unfamiliar city, AND a watchlisted recipient -> enhanced verification.',
  },
  {
  key: '5', label: 'Scenario 5 · Multiple severe indicators', expect: 'CRITICAL',
  recipient_account_number: '1099998888', recipient_name: 'Unknown Wallet Services', amount: '600000',
  resetDevice: true, city: 'Kano', simulated_hour: '3',
  note: 'Watchlisted recipient + new device + new city + extreme amount + 3AM -> blocked + fraud alert.',
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
  const [warning, setWarning] = useState(null)
  const navigate = useNavigate()

  const applyScenario = (s) => {
setError(''); setResult(null); setWarning(null)
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

const buildPayload = () => ({
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
    acknowledged_beneficiary_warning: false,
  })

  const doSubmit = async () => {
  setLoading(true)
  try {
    const res = await api.post('/api/transactions', buildPayload())
    setResult(res.data)

    if (res.data.requires_otp) {
      setTimeout(() => navigate('/verify/otp', { state: { ...res.data } }), 900)
    } else if (res.data.requires_verification) {
      setTimeout(() => navigate('/verify/facial', { state: { ...res.data } }), 900)
    } else if (res.data.status === 'completed') {
      setTimeout(() => navigate(`/receipt/${res.data.transaction_id}`), 900)
    }
  } catch (err) {
    setError(apiErrorMessage(err, 'Transfer could not be processed.'))
  } finally {
    setLoading(false)
  }
}

const submit = async (e) => {
  e.preventDefault()
  setError(''); setResult(null)
  setLoading(true)
  try {
    const { data } = await api.post('/api/transactions/preview', buildPayload())
    if (data.needs_warning) {
      setWarning(data)        // popup shows; nothing has been sent yet
      setLoading(false)
      return
    }
  } catch (err) {
    setError(apiErrorMessage(err, 'Could not check this transfer.'))
    setLoading(false)
    return
  }
  setLoading(false)
  doSubmit()
}

const cancelWarning = () => setWarning(null)

const proceedPastWarning = () => {
  setWarning(null)
  doSubmit()
}

  return (
    <div className="page">
      <div className="container" style={{ maxWidth: 640 }}>
        <div className="page-header">
          <h1>Send money</h1>
          <p>Every transfer is screened by FinShield's multi-layer fraud engine before it completes.</p>
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
            <div className={result.status === 'blocked' ? 'auth-error' : 'auth-info'}
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
              <input
                value={form.recipient_account_number}
                onChange={update('recipient_account_number')}
                maxLength={10} required
              />
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

      {warning && (
  <div className="modal-backdrop" onClick={cancelWarning}>
    <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 440, maxHeight: '85vh', overflow: 'auto' }}>
      <h2 style={{ fontSize: 17, margin: '0 0 8px' }}>⚠️ {warning.headline}</h2>
      <p className="text-muted" style={{ fontSize: 12, margin: '0 0 8px' }}>
        Risk level: <RiskBadge level={warning.risk_level} />
      </p>

      <p style={{ fontSize: 13, fontWeight: 600, margin: '10px 0 4px' }}>What we noticed:</p>
      <ul style={{ fontSize: 13, paddingLeft: 18, margin: 0 }}>
        {warning.scenario.map((s, i) => <li key={i}>{s}</li>)}
      </ul>

      {warning.consequences.length > 0 && (
        <>
          <p style={{ fontSize: 13, fontWeight: 600, margin: '12px 0 4px' }}>If you proceed:</p>
          <ul style={{ fontSize: 13, paddingLeft: 18, margin: 0 }}>
            {warning.consequences.map((c, i) => <li key={i}>{c}</li>)}
          </ul>
        </>
      )}

      <div style={{ display: 'flex', gap: 10, marginTop: 16 }}>
        <button className="btn btn-secondary" onClick={cancelWarning}>Cancel</button>
        <button className="btn btn-primary" onClick={proceedPastWarning}>I understand, proceed</button>
      </div>
    </div>
  </div>
)}
    </div>
  )
}
