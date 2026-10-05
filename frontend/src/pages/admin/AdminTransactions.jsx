import { useEffect, useState } from 'react'
import { adminApi } from '../../services/api'
import RiskBadge from '../../components/RiskBadge'
import StatusPill from '../../components/StatusPill'

export default function AdminTransactions() {
  const [txns, setTxns] = useState([])
  const [loading, setLoading] = useState(true)
  const [riskFilter, setRiskFilter] = useState('')
  const [selected, setSelected] = useState(null)
  const [detail, setDetail] = useState(null)

  const load = async () => {
    setLoading(true)
    const params = new URLSearchParams()
    if (riskFilter) params.set('risk_level', riskFilter)
    const res = await adminApi.get(`/api/admin/transactions?${params.toString()}`)
    setTxns(res.data)
    setLoading(false)
  }

  useEffect(() => { load() }, [riskFilter])

  const openDetail = async (t) => {
    setSelected(t)
    const res = await adminApi.get(`/api/admin/transactions/${t.id}`)
    setDetail(res.data)
  }

  return (
    <div className="page">
      <div className="container">
        <div className="page-header">
          <h1>Transaction monitoring</h1>
          <p>Every transaction FinShield has assessed, with its full risk breakdown.</p>
        </div>

        <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
          {['', 'SAFE', 'CAUTION', 'VERIFY', 'HIGH_RISK', 'CRITICAL'].map(r => (
            <button key={r} className="scenario-btn" onClick={() => setRiskFilter(r)}
              style={riskFilter === r ? { borderColor: 'var(--accent)', color: 'var(--text-primary)' } : {}}>
              {r || 'All'}
            </button>
          ))}
        </div>

        <div className="card">
          {loading ? <div className="empty-state">Loading…</div> : txns.length === 0 ? (
            <div className="empty-state">No transactions match this filter.</div>
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>User</th><th>Amount</th><th>Recipient</th><th>Device</th><th>Location</th>
                    <th>Risk</th><th>Status</th><th>Investigation</th><th>Date</th>
                  </tr>
                </thead>
                <tbody>
                  {txns.map(t => (
                    <tr key={t.id} className="clickable" onClick={() => openDetail(t)}>
                      <td>{t.user_name}</td>
                      <td className="mono">₦{Number(t.amount).toLocaleString()}</td>
                      <td>{t.recipient_name || t.recipient_account_number}</td>
                      <td className="text-secondary" style={{ fontSize: 12 }}>{t.operating_system} · {t.browser}</td>
                      <td className="text-secondary">{t.city}, {t.country}</td>
                      <td><RiskBadge level={t.risk_level} /></td>
                      <td><StatusPill status={t.status} /></td>
                      <td className="text-muted" style={{ textTransform: 'capitalize' }}>{t.investigation_status.replace('_', ' ')}</td>
                      <td className="text-muted">{new Date(t.created_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {selected && (
        <div className="modal-backdrop" onClick={() => { setSelected(null); setDetail(null) }}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            {!detail ? <div className="empty-state">Loading…</div> : (
              <>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <div className="mono text-muted" style={{ fontSize: 12 }}>{detail.reference}</div>
                    <h2 style={{ margin: '4px 0 0', fontSize: 20 }}>₦{Number(detail.amount).toLocaleString()}</h2>
                  </div>
                  <RiskBadge level={detail.risk_level} />
                </div>

                <div className="grid grid-2" style={{ marginTop: 18, gap: 12 }}>
                  <div>
                    <div className="stat-label">Sender</div>
                    <div style={{ fontSize: 13.5, marginTop: 4 }}>{detail.user?.full_name}</div>
                    <div className="text-muted" style={{ fontSize: 12 }}>{detail.user?.email}</div>
                  </div>
                  <div>
                    <div className="stat-label">Recipient</div>
                    <div style={{ fontSize: 13.5, marginTop: 4 }}>{detail.recipient_name || '—'}</div>
                    <div className="text-muted mono" style={{ fontSize: 12 }}>{detail.recipient_account_number}</div>
                  </div>
                  <div>
                    <div className="stat-label">Device</div>
                    <div style={{ fontSize: 13.5, marginTop: 4 }}>{detail.operating_system} · {detail.browser}</div>
                  </div>
                  <div>
                    <div className="stat-label">Location</div>
                    <div style={{ fontSize: 13.5, marginTop: 4 }}>{detail.city}, {detail.country}</div>
                  </div>
                  <div>
                    <div className="stat-label">Status</div>
                    <div style={{ marginTop: 4 }}><StatusPill status={detail.status} /></div>
                  </div>
                  <div>
                    <div className="stat-label">Engine version</div>
                    <div className="mono" style={{ fontSize: 13.5, marginTop: 4 }}>FinShield rule v{detail.fraud_rule_version}</div>
                  </div>
                </div>

                <div style={{ marginTop: 18 }}>
                  <div className="stat-label">Triggered risk indicators</div>
                  <ul className="factor-list">
                    {(detail.risk_factors || []).map((f, i) => <li key={i}>{f}</li>)}
                  </ul>
                </div>

                <button className="btn btn-secondary" style={{ marginTop: 20 }} onClick={() => { setSelected(null); setDetail(null) }}>
                  Close
                </button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
