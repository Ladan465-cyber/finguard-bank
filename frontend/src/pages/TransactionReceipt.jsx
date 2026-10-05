import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { api, apiErrorMessage } from '../services/api'

export default function TransactionReceipt() {
  const { id } = useParams()
  const [r, setR] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get(`/api/transactions/${id}/receipt`)
      .then(res => setR(res.data))
      .catch(err => setError(apiErrorMessage(err, 'Could not load this receipt.')))
  }, [id])

  if (error) return <div className="page"><div className="container"><div className="auth-error">{error}</div></div></div>
  if (!r) return <div className="page"><div className="container"><div className="empty-state">Loading…</div></div></div>

  const done = r.status === 'completed'
  const row = (label, value) => (
    <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border, #eee)' }}>
      <span className="text-muted">{label}</span><span>{value}</span>
    </div>
  )

  return (
    <div className="page">
      <div className="container" style={{ maxWidth: 520 }}>
        <div className="card">
          <div style={{ textAlign: 'center', marginBottom: 16 }}>
            <div style={{ fontSize: 40 }}>{done ? '✅' : 'ℹ️'}</div>
            <h1 style={{ fontSize: 20, margin: '6px 0' }}>
              {done ? 'Transaction successful' : `Transaction ${r.status}`}
            </h1>
            <div style={{ fontSize: 26, fontWeight: 700 }}>₦{Number(r.amount).toLocaleString()}</div>
          </div>

          {row('Recipient', r.recipient_name || '—')}
          {row('Account number', r.recipient_account_number)}
          {row('Bank', r.recipient_bank || '—')}
          {row('Reference', <span className="mono">{r.reference}</span>)}
          {r.narration && row('Narration', r.narration)}
          {row('Date', new Date(r.completed_at || r.created_at).toLocaleString())}
          {row('Risk assessment', <span className="badge">{r.risk_level}</span>)}

          <h3 style={{ fontSize: 14, margin: '18px 0 6px' }}>What happened in this transaction</h3>
          <p style={{ fontSize: 13, margin: '0 0 6px' }}><b>{r.headline}</b></p>
          <ul style={{ fontSize: 13, paddingLeft: 18, margin: 0 }}>
            {r.scenario.map((s, i) => <li key={i}>{s}</li>)}
          </ul>

          {r.consequences.length > 0 && (
            <>
              <h3 style={{ fontSize: 14, margin: '18px 0 6px' }}>What this could mean for you</h3>
              <ul style={{ fontSize: 13, paddingLeft: 18, margin: 0 }}>
                {r.consequences.map((c, i) => <li key={i}>{c}</li>)}
              </ul>
            </>
          )}

          <div style={{ display: 'flex', gap: 10, marginTop: 20 }}>
            <Link to="/transfer" className="btn btn-primary" style={{ flex: 1, textAlign: 'center' }}>New transfer</Link>
            <Link to="/history" className="btn btn-secondary" style={{ flex: 1, textAlign: 'center' }}>History</Link>
          </div>
        </div>
      </div>
    </div>
  )
}