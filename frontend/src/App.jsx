import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './AuthContext'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Environments from './pages/Environments'
import NewEnvironment from './pages/NewEnvironment'
import EnvironmentDetail from './pages/EnvironmentDetail'
import Settings from './pages/Settings'
import Billing from './pages/Billing'
import Account from './pages/Account'
import Help from './pages/Help'
import PlatformPlaceholder from './pages/PlatformPlaceholder'
import './styles.css'

function ProtectedRoute({ children }) {
  const { me, loading } = useAuth()
  if (loading) return <div className="page-loading">Loading…</div>
  if (!me?.logged_in) return <Navigate to="/login" replace />
  return children
}

function RootRedirect() {
  const { me, loading } = useAuth()
  if (loading) return <div className="page-loading">Loading…</div>
  return <Navigate to={me?.logged_in ? '/dashboard' : '/login'} replace />
}

function wrap(Component) {
  return (
    <ProtectedRoute>
      <Component />
    </ProtectedRoute>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<RootRedirect />} />
          <Route path="/login" element={<Login />} />
          <Route path="/dashboard" element={wrap(Dashboard)} />
          <Route path="/environments" element={wrap(Environments)} />
          <Route path="/environments/new" element={wrap(NewEnvironment)} />
          <Route path="/environments/:uuid" element={wrap(EnvironmentDetail)} />
          <Route path="/billing" element={wrap(Billing)} />
          <Route path="/account" element={wrap(Account)} />
          <Route path="/settings" element={wrap(Settings)} />
          <Route path="/help" element={wrap(Help)} />
          <Route path="/platform/:section" element={wrap(PlatformPlaceholder)} />
          <Route path="/platform/:section/:sub" element={wrap(PlatformPlaceholder)} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
