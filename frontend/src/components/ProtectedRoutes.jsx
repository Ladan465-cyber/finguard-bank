import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { useAdminAuth } from '../context/AdminAuthContext'

export function ProtectedRoute({ children }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="empty-state">Loading…</div>
  if (!user) return <Navigate to="/login" replace />
  return children
}

export function AdminProtectedRoute({ children }) {
  const { admin, loading } = useAdminAuth()
  if (loading) return <div className="empty-state">Loading…</div>
  if (!admin) return <Navigate to="/admin/login" replace />
  return children
}
