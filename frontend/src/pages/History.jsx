import { useEffect, useState } from 'react'
import { api } from '../services/api'
import RiskBadge from '../components/RiskBadge'
import StatusPill from '../components/StatusPill'

export default function History() {
  const [txns, setTxns] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/api/transactions/history').then(res => { setTxns(res.data); setLoading(false) })
  }, [])

  return (
    <div className="page">
      <div className="container">
        <div className="page-header">
          <h1>Transaction history</h1>
          <p>All your transfers, including their FinShield risk outcome.</p>
        </div>

        <div className="card">
          {loading ? <div className="empty-state">Loading…</div> : txns.length === 0 ? (
            <div className="empty-state">No transactions yet.</div>
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr><th>Reference</th><th>Recipient</th><th>Amount</th><th>Type</th><th>Risk</th><th>Status</th><th>Date</th></tr>
                </thead>
                <tbody>
                  {txns.map(t => (
                    <tr key={t.id}>
                      <td className="mono text-muted">{t.reference}</td>
                      <td>{t.recipient_name || t.recipient_account_number}</td>
                      <td className="mono">₦{Number(t.amount).toLocaleString()}</td>
                      <td className="text-secondary">{t.transaction_type}</td>
                      <td><RiskBadge level={t.risk_level} /></td>
                      <td><StatusPill status={t.status} /></td>
                      <td className="text-muted">{new Date(t.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
