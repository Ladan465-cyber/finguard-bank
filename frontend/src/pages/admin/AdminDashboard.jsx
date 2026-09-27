import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { adminApi } from '../../services/api'
import RiskBadge from '../../components/RiskBadge'

export default function AdminDashboard() {
  const [stats, setStats] = useState(null)
  const [recent, setRecent] = useState([])

  useEffect(() => {
    (async () => {
      const [s, alerts] = await Promise.all([
        adminApi.get('/api/admin/dashboard/stats'),
        adminApi.get('/api/admin/fraud-alerts?limit=6'),
      ])
      setStats(s.data)
      setRecent(alerts.data)
    })()
  }, [])

  const cards = stats ? [
    { label: 'Total transactions', value: stats.total_transactions },
    { label: 'Successful', value: stats.successful_transactions, color: 'var(--low)' },
    { label: 'Blocked', value: stats.blocked_transactions, color: 'var(--critical)' },
    { label: 'Awaiting verification', value: stats.transactions_requiring_verification, color: 'var(--medium)' },
    { label: 'Open fraud alerts', value: stats.open_fraud_alerts, color: 'var(--critical)' },
    { label: 'High risk txns', value: stats.high_risk_transactions, color: 'var(--high)' },
    { label: 'Critical risk txns', value: stats.critical_risk_transactions, color: 'var(--critical)' },
    { label: 'Transactions (24h)', value: stats.transactions_last_24h },
  ] : []

  return (
    <div className="page">
      <div className="container">
        <div className="page-header">
          <h1>Fraud monitoring overview</h1>
          <p>Real-time snapshot of transaction and fraud activity across FinGuard Bank.</p>
        </div>

        <div className="grid grid-4" style={{ marginBottom: 22 }}>
          {cards.map(c => (
            <div className="card stat-card" key={c.label}>
              <div className="stat-label">{c.label}</div>
              <div className="stat-value" style={{ color: c.color || 'var(--text-primary)' }}>{c.value}</div>
            </div>
          ))}
        </div>

        {stats && (
          <div className="card" style={{ marginBottom: 22 }}>
            <div className="stat-label">Total completed volume</div>
            <div className="stat-value" style={{ fontSize: 22 }}>₦{Number(stats.total_completed_volume_ngn).toLocaleString()}</div>
          </div>
        )}

        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <h3 style={{ margin: 0, fontSize: 15 }}>Latest fraud alerts</h3>
            <Link to="/admin/alerts" style={{ fontSize: 13, color: 'var(--accent)' }}>View all →</Link>
          </div>
          {recent.length === 0 ? <div className="empty-state">No fraud alerts yet.</div> : (
            <div className="table-wrap">
              <table className="data-table">
                <thead><tr><th>User</th><th>Amount</th><th>Risk</th><th>Top factor</th><th>Status</th><th>Date</th></tr></thead>
                <tbody>
                  {recent.map(e => (
                    <tr key={e.id}>
                      <td>{e.user_name}</td>
                      <td className="mono">₦{Number(e.amount).toLocaleString()}</td>
                      <td><RiskBadge level={e.risk_level} /></td>
                      <td className="text-secondary" style={{ maxWidth: 320 }}>{e.risk_factors?.[0]}</td>
                      <td className="text-secondary">{e.status.replace('_', ' ')}</td>
                      <td className="text-muted">{new Date(e.created_at).toLocaleString()}</td>
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
