import { useState } from 'react'
import './App.css'
import { AppHeader } from './components/AppHeader'
import { AssistantWorkspace } from './components/AssistantWorkspace'
import { QuickActions } from './components/QuickActions'
import { VehicleOverview } from './components/VehicleOverview'

const demoVehicle = {
  ownerName: 'Avery Singh',
  manufacturer: 'Aster Motors',
  model: 'Comet',
  modelYear: 2023,
  currentOdometerKm: 12_500,
  serviceIntervalKm: 10_000,
  serviceIntervalMonths: 12,
  latestScheduledServiceDate: '15 Jul 2026',
  latestScheduledServiceOdometerKm: 12_000,
} as const

function App() {
  const [assistantDraft, setAssistantDraft] = useState('')

  return (
    <div className="app-shell">
      <AppHeader />

      <main className="dashboard">
        <section className="dashboard__intro" aria-labelledby="dashboard-title">
          <div>
            <p className="eyebrow">Avery&apos;s garage</p>
            <h1 id="dashboard-title">Your vehicle, clearly understood.</h1>
          </div>
          <p className="dashboard__intro-copy">
            Review the essentials, check maintenance, or ask for grounded ownership support.
          </p>
        </section>

        <div className="dashboard__grid">
          <div className="ownership-column">
            <VehicleOverview vehicle={demoVehicle} />
            <QuickActions onSelect={setAssistantDraft} />
          </div>

          <AssistantWorkspace
            draft={assistantDraft}
            onDraftChange={setAssistantDraft}
          />
        </div>
      </main>

      <footer className="app-footer">
        <span>Ownership Copilot</span>
        <span>Demo experience · Synthetic vehicle data</span>
      </footer>
    </div>
  )
}

export default App
