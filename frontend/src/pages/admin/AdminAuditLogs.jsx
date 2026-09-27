import { useEffect, useState } from 'react'
import { adminApi } from '../../services/api'

export default function AdminAuditLogs() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    adminApi.get('/api/admin/audit-logs').then(res => { setLogs(res.data); setLoading(false) })
  }, [])

  return (
    <div className="page">
      <div className="container">
        <div className="page-header">
          <h1>Audit logs</h1>
          <p>Append-only trail of security-relevant events across the platform.</p>
        </div>

        <div className="card">
          {loading ? <div className="empty-state">Loading…</div> : logs.length === 0 ? (
            <div className="empty-state">No audit entries yet.</div>
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr><th>Actor</th><th>Action</th><th>Entity</th><th>Details</th><th>Time</th></tr>
                </thead>
                <tbody>
                  {logs.map(l => (
                    <tr key={l.id}>
                      <td className="text-secondary" style={{ textTransform: 'capitalize' }}>{l.actor_type}</td>
                      <td><span className="badge">{l.action}</span></td>
                      <td className="text-muted">{l.entity_type ? `${l.entity_type} · ${l.entity_id?.slice(0, 8)}…` : '—'}</td>
                      <td className="text-muted" style={{ fontSize: 12, maxWidth: 320 }}>
                        {l.details && Object.keys(l.details).length > 0 ? JSON.stringify(l.details) : '—'}
                      </td>
                      <td className="text-muted">{new Date(l.created_at).toLocaleString()}</td>
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
