import { useEffect, useState } from 'react'
import { adminApi, apiErrorMessage } from '../../services/api'

const CATEGORIES = ['TRUSTED', 'WATCHLISTED', 'HIGH_RISK']

export default function AdminBeneficiaries() {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    account_number: '', risk_category: 'WATCHLISTED', reason: '', tags: '',
    fraud_report_count: 0, complaint_count: 0,
  })
  const [saving, setSaving] = useState(false)

  const load = async () => {
    setLoading(true)
    const res = await adminApi.get('/api/admin/beneficiaries')
    setRows(res.data)
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const update = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    setError(''); setSaving(true)
    try {
      await adminApi.post('/api/admin/beneficiaries', {
        account_number: form.account_number,
        risk_category: form.risk_category,
        reason: form.reason || undefined,
        tags: form.tags ? form.tags.split(',').map(t => t.trim()).filter(Boolean) : [],
        fraud_report_count: parseInt(form.fraud_report_count, 10) || 0,
        complaint_count: parseInt(form.complaint_count, 10) || 0,
      })
      setForm({ account_number: '', risk_category: 'WATCHLISTED', reason: '', tags: '', fraud_report_count: 0, complaint_count: 0 })
      setShowForm(false)
      await load()
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not save this entry.'))
    } finally {
      setSaving(false)
    }
  }

  const remove = async (id) => {
    await adminApi.delete(`/api/admin/beneficiaries/${id}`)
    await load()
  }

  return (
    <div className="page">
      <div className="container">
        <div className="page-header">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div>
              <h1>Beneficiary watchlist</h1>
              <p>Fraud intelligence about recipient accounts -- powers the pre-submit warning modal and the Beneficiary Risk layer.</p>
            </div>
            <button className="btn btn-primary" style={{ width: 'auto' }} onClick={() => setShowForm(s => !s)}>
              {showForm ? 'Cancel' : '+ Add entry'}
            </button>
          </div>
        </div>

        {showForm && (
          <div className="card" style={{ marginBottom: 20 }}>
            {error && <div className="auth-error">{error}</div>}
            <form onSubmit={submit}>
              <div className="grid grid-2">
                <div className="field">
                  <label>Account number</label>
                  <input value={form.account_number} onChange={update('account_number')} maxLength={10} required />
                </div>
                <div className="field">
                  <label>Risk category</label>
                  <select value={form.risk_category} onChange={update('risk_category')}>
                    {CATEGORIES.map(c => <option key={c} value={c}>{c}</option>)}
                  </select>
                </div>
              </div>
              <div className="field">
                <label>Reason (shown to admins and in the customer warning)</label>
                <input value={form.reason} onChange={update('reason')} placeholder="e.g. Confirmed Ponzi scheme, multiple complaints" />
              </div>
              <div className="field">
                <label>Tags (comma-separated)</label>
                <input value={form.tags} onChange={update('tags')} placeholder="ponzi_scheme, mule_account" />
              </div>
              <div className="grid grid-2">
                <div className="field">
                  <label>Fraud report count</label>
                  <input type="number" min="0" value={form.fraud_report_count} onChange={update('fraud_report_count')} />
                </div>
                <div className="field">
                  <label>Complaint count</label>
                  <input type="number" min="0" value={form.complaint_count} onChange={update('complaint_count')} />
                </div>
              </div>
              <button className="btn btn-primary" disabled={saving}>{saving ? 'Saving…' : 'Save to watchlist'}</button>
            </form>
          </div>
        )}

        <div className="card">
          {loading ? <div className="empty-state">Loading…</div> : rows.length === 0 ? (
            <div className="empty-state">No beneficiary risk entries yet.</div>
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr><th>Account</th><th>Category</th><th>Reason</th><th>Tags</th><th>Reports</th><th>Complaints</th><th></th></tr>
                </thead>
                <tbody>
                  {rows.map(b => (
                    <tr key={b.id}>
                      <td className="mono">{b.account_number}</td>
                      <td><span className={`risk-badge risk-${b.risk_category === 'TRUSTED' ? 'SAFE' : b.risk_category}`}>{b.risk_category}</span></td>
                      <td className="text-secondary" style={{ maxWidth: 280 }}>{b.reason || '—'}</td>
                      <td>
                        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
                          {(b.tags || []).map(t => <span key={t} className="badge">{t.replace(/_/g, ' ')}</span>)}
                        </div>
                      </td>
                      <td className="mono">{b.fraud_report_count}</td>
                      <td className="mono">{b.complaint_count}</td>
                      <td><button className="btn btn-secondary btn-sm" onClick={() => remove(b.id)}>Remove</button></td>
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
