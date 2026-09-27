import { useEffect, useState } from 'react'
import { adminApi } from '../../services/api'
import RiskBadge from '../../components/RiskBadge'

export default function AdminFraudAlerts() {
  const [alerts, setAlerts] = useState([])
  const [loading, setLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState('open')
  const [busyId, setBusyId] = useState(null)

  const load = async () => {
    setLoading(true)
    const params = new URLSearchParams()
    if (statusFilter) params.set('status', statusFilter)
    const res = await adminApi.get(`/api/admin/fraud-alerts?${params.toString()}`)
    setAlerts(res.data)
    setLoading(false)
  }

  useEffect(() => { load() }, [statusFilter])

  const resolve = async (id, resolution) => {
    setBusyId(id)
    try {
      await adminApi.post(`/api/admin/fraud-alerts/${id}/resolve?resolution=${resolution}`)
      await load()
    } finally {
      setBusyId(null)
    }
  }

  return (
    <div className="page">
      <div className="container">
        <div className="page-header">
          <h1>Fraud alerts</h1>
          <p>Transactions FinShield flagged MEDIUM risk or above, for analyst review.</p>
        </div>

        <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          {[
            { key: 'open', label: 'Open' },
            { key: 'reviewing', label: 'Reviewing' },
            { key: 'resolved_fraud', label: 'Confirmed fraud' },
            { key: 'resolved_legitimate', label: 'Confirmed legitimate' },
            { key: '', label: 'All' },
          ].map(o => (
            <button key={o.key} className="scenario-btn" onClick={() => setStatusFilter(o.key)}
              style={statusFilter === o.key ? { borderColor: 'var(--accent)', color: 'var(--text-primary)' } : {}}>
              {o.label}
            </button>
          ))}
        </div>

        {loading ? <div className="card empty-state">Loading…</div> : alerts.length === 0 ? (
          <div className="card empty-state">No alerts in this view.</div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            {alerts.map(a => (
              <div className="card" key={a.id}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                      <RiskBadge level={a.risk_level} />
                      <span className="mono text-muted" style={{ fontSize: 12 }}>{a.transaction_reference}</span>
                    </div>
                    <h3 style={{ margin: '10px 0 2px', fontSize: 16 }}>{a.user_name} · ₦{Number(a.amount).toLocaleString()}</h3>
                    <div className="text-muted" style={{ fontSize: 12 }}>{new Date(a.created_at).toLocaleString()} · Score {a.risk_score}/100</div>
                  </div>
                  {a.status === 'open' && (
                    <div style={{ display: 'flex', gap: 8 }}>
                      <button className="btn btn-secondary btn-sm" disabled={busyId === a.id} onClick={() => resolve(a.id, 'resolved_legitimate')}>
                        Mark legitimate
                      </button>
                      <button className="btn btn-danger btn-sm" disabled={busyId === a.id} onClick={() => resolve(a.id, 'resolved_fraud')}>
                        Confirm fraud
                      </button>
                    </div>
                  )}
                  {a.status !== 'open' && <span className="status-pill">{a.status.replace('_', ' ')}</span>}
                </div>

                <ul className="factor-list" style={{ marginTop: 14 }}>
                  {(a.risk_factors || []).map((f, i) => <li key={i}>{f}</li>)}
                </ul>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
