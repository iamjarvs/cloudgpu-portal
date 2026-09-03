import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { api } from './api'

const AuthContext = createContext(null)

export function useAuth() {
  return useContext(AuthContext)
}

export function AuthProvider({ children }) {
  const [me, setMe] = useState(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    try {
      const data = await api.me()
      setMe(data)
    } catch (_) {
      setMe({ logged_in: false, tenant_display_name: 'HeliosGrid' })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    refresh()
  }, [refresh])

  return <AuthContext.Provider value={{ me, loading, refresh }}>{children}</AuthContext.Provider>
}
