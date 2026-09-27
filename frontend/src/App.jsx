import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'

import { AuthProvider } from './context/AuthContext'
import { AdminAuthProvider } from './context/AdminAuthContext'
import { ProtectedRoute, AdminProtectedRoute } from './components/ProtectedRoutes'

import Navbar from './components/Navbar'
import AdminNavbar from './components/AdminNavbar'

import Login from './pages/Login'
import Register from './pages/Register'
import Dashboard from './pages/Dashboard'
import Transfer from './pages/Transfer'
import History from './pages/History'
import Devices from './pages/Devices'
import VerifyOtp from './pages/VerifyOtp'
import VerifyFacial from './pages/VerifyFacial'

import AdminLogin from './pages/admin/AdminLogin'
import AdminDashboard from './pages/admin/AdminDashboard'
import AdminTransactions from './pages/admin/AdminTransactions'
import AdminFraudAlerts from './pages/admin/AdminFraudAlerts'
import AdminAuditLogs from './pages/admin/AdminAuditLogs'

function CustomerLayout({ children }) {
  return (
    <div className="app-shell">
      <Navbar />
      {children}
    </div>
  )
}

function AdminLayout({ children }) {
  return (
    <div className="app-shell">
      <AdminNavbar />
      {children}
    </div>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <AdminAuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Navigate to="/login" replace />} />
            <Route path="/login" element={<Login />} />
            <Route path="/register" element={<Register />} />

            <Route path="/dashboard" element={
              <ProtectedRoute><CustomerLayout><Dashboard /></CustomerLayout></ProtectedRoute>
            } />
            <Route path="/transfer" element={
              <ProtectedRoute><CustomerLayout><Transfer /></CustomerLayout></ProtectedRoute>
            } />
            <Route path="/history" element={
              <ProtectedRoute><CustomerLayout><History /></CustomerLayout></ProtectedRoute>
            } />
            <Route path="/devices" element={
              <ProtectedRoute><CustomerLayout><Devices /></CustomerLayout></ProtectedRoute>
            } />
            <Route path="/verify/otp" element={
              <ProtectedRoute><CustomerLayout><VerifyOtp /></CustomerLayout></ProtectedRoute>
            } />
            <Route path="/verify/facial" element={
              <ProtectedRoute><CustomerLayout><VerifyFacial /></CustomerLayout></ProtectedRoute>
            } />

            <Route path="/admin/login" element={<AdminLogin />} />
            <Route path="/admin/dashboard" element={
              <AdminProtectedRoute><AdminLayout><AdminDashboard /></AdminLayout></AdminProtectedRoute>
            } />
            <Route path="/admin/transactions" element={
              <AdminProtectedRoute><AdminLayout><AdminTransactions /></AdminLayout></AdminProtectedRoute>
            } />
            <Route path="/admin/alerts" element={
              <AdminProtectedRoute><AdminLayout><AdminFraudAlerts /></AdminLayout></AdminProtectedRoute>
            } />
            <Route path="/admin/audit-logs" element={
              <AdminProtectedRoute><AdminLayout><AdminAuditLogs /></AdminLayout></AdminProtectedRoute>
            } />

            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        </BrowserRouter>
      </AdminAuthProvider>
    </AuthProvider>
  )
}
