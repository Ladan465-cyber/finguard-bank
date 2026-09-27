import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { api } from '../services/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const loadUser = useCallback(async () => {
    const token = localStorage.getItem('fg_token')
    if (!token) { setLoading(false); return }
    try {
      const res = await api.get('/api/auth/me')
      setUser(res.data)
    } catch {
      localStorage.removeItem('fg_token')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { loadUser() }, [loadUser])

  const login = (token, name, id) => {
    localStorage.setItem('fg_token', token)
    setUser({ full_name: name, id })
    loadUser()
  }

  const logout = () => {
    localStorage.removeItem('fg_token')
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refresh: loadUser }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
