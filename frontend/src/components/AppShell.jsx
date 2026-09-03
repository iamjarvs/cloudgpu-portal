import Sidebar from './Sidebar'
import Header from './Header'

export default function AppShell({ title, narrow, children }) {
  return (
    <div className="shell">
      <Sidebar />
      <div className="shell-main">
        <Header title={title} />
        <main className={`shell-content${narrow ? ' narrow' : ''}`}>{children}</main>
      </div>
    </div>
  )
}
