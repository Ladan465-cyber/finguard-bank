import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../services/api'
import { useAuth } from '../context/AuthContext'
import RiskBadge from '../components/RiskBadge'
import StatusPill from '../components/StatusPill'

export default function Dashboard() {
  const { user } = useAuth()
  const [balance, setBalance] = useState(null)
  const [txns, setTxns] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    (async () => {
      const [bal, hist] = await Promise.all([
        api.get('/api/account/balance'),
        api.get('/api/transactions/history'),
      ])
      setBalance(bal.data)
      setTxns(hist.data.slice(0, 6))
      setLoading(false)
    })()
  }, [])

  const completed = txns.filter(t => t.status === 'completed').length
  const flagged = txns.filter(t => t.risk_level && t.risk_level !== 'SAFE').length

  return (
    <div className="page">
      <div className="container">
        <div className="page-header">
          <h1>Welcome back, {user?.full_name?.split(' ')[0] || 'there'} 👋</h1>
          <p>Here's what's happening with your account.</p>
        </div>

        <div className="grid grid-2" style={{ marginBottom: 22 }}>
          <div className="balance-hero">
            <div className="balance-label">Available balance</div>
            <div className="balance-amount">
              {balance ? `₦${Number(balance.balance).toLocaleString()}` : '—'}
            </div>
            <div className="balance-acct">{balance?.bank_name} · Acct No. {balance?.account_number}</div>
            <div style={{ marginTop: 18, display: 'flex', gap: 10 }}>
              <Link to="/transfer" className="btn btn-primary" style={{ width: 'auto' }}>Send money</Link>
              <Link to="/history" className="btn btn-secondary" style={{ width: 'auto' }}>View history</Link>
            </div>
          </div>

          <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: 18 }}>
            <div className="card stat-card">
              <div className="stat-label">Recent transactions</div>
              <div className="stat-value">{txns.length}</div>
              <div className="stat-sub">{completed} completed</div>
            </div>
            <div className="card stat-card">
              <div className="stat-label">Flagged for review</div>
              <div className="stat-value" style={{ color: flagged ? 'var(--high)' : 'var(--low)' }}>{flagged}</div>
              <div className="stat-sub">out of last {txns.length}</div>
            </div>
            <div className="card stat-card" style={{ gridColumn: '1 / -1' }}>
              <div className="stat-label">FinShield protection</div>
              <div className="stat-sub" style={{ marginTop: 8, fontSize: 13 }}>
                Every transfer you make is screened in real time against your
                normal spending behaviour, devices and locations.
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <h3 style={{ margin: 0, fontSize: 15 }}>Recent activity</h3>
            <Link to="/history" style={{ fontSize: 13, color: 'var(--accent)' }}>View all →</Link>
          </div>
          {loading ? <div className="empty-state">Loading…</div> : txns.length === 0 ? (
            <div className="empty-state">No transactions yet. <Link to="/transfer">Send your first transfer</Link>.</div>
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr><th>Recipient</th><th>Amount</th><th>Risk</th><th>Status</th><th>Date</th></tr>
                </thead>
                <tbody>
                  {txns.map(t => (
                    <tr key={t.id}>
                      <td>{t.recipient_name || t.recipient_account_number}</td>
                      <td className="mono">₦{Number(t.amount).toLocaleString()}</td>
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
