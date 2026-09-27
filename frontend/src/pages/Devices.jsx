import { useEffect, useState } from 'react'
import { api, apiErrorMessage } from '../services/api'
import { getDeviceFingerprint } from '../services/device'
import FaceCapture from '../components/FaceCapture'

export default function Devices() {
  const [devices, setDevices] = useState([])
  const [loading, setLoading] = useState(true)
  const [faceEnrolled, setFaceEnrolled] = useState(null)
  const [enrolling, setEnrolling] = useState(false)
  const [enrollError, setEnrollError] = useState('')
  const [enrollSuccess, setEnrollSuccess] = useState('')
  const currentFp = getDeviceFingerprint()

  useEffect(() => {
    api.get('/api/account/devices').then(res => { setDevices(res.data); setLoading(false) })
    api.get('/api/account/face-status').then(res => setFaceEnrolled(res.data.enrolled))
  }, [])

  const handleEnroll = async (descriptor) => {
    setEnrollError(''); setEnrollSuccess('')
    try {
      await api.post('/api/account/face-enroll', { descriptor })
      setFaceEnrolled(true)
      setEnrolling(false)
      setEnrollSuccess('Face ID set up successfully. This will be used the next time a transaction requires identity verification.')
    } catch (err) {
      setEnrollError(apiErrorMessage(err, 'Could not save your Face ID. Please try again.'))
    }
  }

  return (
    <div className="page">
      <div className="container">
        <div className="page-header">
          <h1>Security &amp; devices</h1>
          <p>Devices FinShield has seen on your account, plus your Face ID for high-risk identity verification.</p>
        </div>

        <div className="card" style={{ marginBottom: 22 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 6 }}>
            <div>
              <h3 style={{ margin: 0, fontSize: 15 }}>Face ID</h3>
              <p className="text-muted" style={{ fontSize: 13, marginTop: 4, maxWidth: 460 }}>
                Used for HIGH-risk transactions (e.g. a new device combined with an unusual
                location). We store only a numeric face descriptor, never a photo.
              </p>
            </div>
            {faceEnrolled !== null && (
              <span className={`badge ${faceEnrolled ? 'badge-trusted' : 'badge-new'}`}>
                {faceEnrolled ? 'Enrolled' : 'Not enrolled'}
              </span>
            )}
          </div>

          {enrollSuccess && <div className="auth-info" style={{ background: 'var(--low-bg)', color: 'var(--low)' }}>{enrollSuccess}</div>}
          {enrollError && <div className="auth-error">{enrollError}</div>}

          {!enrolling ? (
            <button className="btn btn-secondary" style={{ width: 'auto' }} onClick={() => { setEnrolling(true); setEnrollSuccess('') }}>
              {faceEnrolled ? 'Re-enroll my face' : 'Set up Face ID'}
            </button>
          ) : (
            <div style={{ maxWidth: 360 }}>
              <FaceCapture
                buttonLabel="Save this as my Face ID"
                helperText="Look directly at the camera in good lighting, then capture."
                onDescriptor={handleEnroll}
              />
              <button className="btn btn-secondary" style={{ marginTop: 10 }} onClick={() => setEnrolling(false)}>
                Cancel
              </button>
            </div>
          )}
        </div>

        <div className="card">
          <h3 style={{ margin: '0 0 14px', fontSize: 15 }}>Known devices</h3>
          {loading ? <div className="empty-state">Loading…</div> : devices.length === 0 ? (
            <div className="empty-state">No devices recorded yet.</div>
          ) : (
            <div className="table-wrap">
              <table className="data-table">
                <thead>
                  <tr><th>Device</th><th>Status</th><th>First seen</th><th>Last seen</th><th>Times used</th></tr>
                </thead>
                <tbody>
                  {devices.map(d => (
                    <tr key={d.id}>
                      <td>{d.device_name}</td>
                      <td>
                        <span className={`badge ${d.is_trusted ? 'badge-trusted' : 'badge-new'}`}>
                          {d.is_trusted ? 'Trusted' : 'New'}
                        </span>
                      </td>
                      <td className="text-muted">{new Date(d.first_seen_at).toLocaleDateString()}</td>
                      <td className="text-muted">{new Date(d.last_seen_at).toLocaleString()}</td>
                      <td className="mono">{d.times_used}</td>
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