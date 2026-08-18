import { CarFront, CircleUserRound, ShieldCheck } from 'lucide-react'

export function AppHeader() {
  return (
    <header className="app-header">
      <a className="brand" href="/" aria-label="Ownership Copilot home">
        <span className="brand__mark" aria-hidden="true">
          <CarFront size={20} strokeWidth={1.8} />
        </span>
        <span className="brand__copy">
          <strong>Ownership Copilot</strong>
          <span>Vehicle support &amp; maintenance</span>
        </span>
      </a>

      <div className="header-context" aria-label="Current workspace">
        <span className="demo-badge">
          <span className="demo-badge__dot" aria-hidden="true" />
          Demo workspace
        </span>
        <span className="header-trust">
          <ShieldCheck size={16} aria-hidden="true" />
          Deterministic service status
        </span>
        <span className="header-divider" aria-hidden="true" />
        <span className="owner-chip">
          <CircleUserRound size={18} aria-hidden="true" />
          Avery Singh
        </span>
      </div>
    </header>
  )
}
