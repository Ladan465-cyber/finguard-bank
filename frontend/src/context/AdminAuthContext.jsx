import { createContext, useContext, useState, useEffect } from 'react'

const AdminAuthContext = createContext(null)

export function AdminAuthProvider({ children }) {
  const [admin, setAdmin] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem('fg_admin_token')
    const name = localStorage.getItem('fg_admin_name')
    if (token && name) setAdmin({ name })
    setLoading(false)
  }, [])

  const login = (token, name) => {
    localStorage.setItem('fg_admin_token', token)
    localStorage.setItem('fg_admin_name', name)
    setAdmin({ name })
  }

  const logout = () => {
    localStorage.removeItem('fg_admin_token')
    localStorage.removeItem('fg_admin_name')
    setAdmin(null)
  }

  return (
    <AdminAuthContext.Provider value={{ admin, loading, login, logout }}>
      {children}
    </AdminAuthContext.Provider>
  )
}

export const useAdminAuth = () => useContext(AdminAuthContext)
