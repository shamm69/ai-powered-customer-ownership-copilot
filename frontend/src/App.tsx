import './App.css'

function App() {
  return (
    <main className="foundation">
      <header className="foundation__header">
        <a className="brand" href="/" aria-label="Customer Ownership Copilot home">
          <span className="brand__mark" aria-hidden="true">
            CO
          </span>
          <span className="brand__name">Ownership Copilot</span>
        </a>
        <span className="phase-label">Phase 5 foundation</span>
      </header>

      <section className="foundation__content" aria-labelledby="foundation-title">
        <div className="foundation__copy">
          <p className="eyebrow">Automotive ownership, clearly connected</p>
          <h1 id="foundation-title">A confident home for every ownership moment.</h1>
          <p className="foundation__description">
            The interface foundation is ready for a polished vehicle dashboard
            and an assistant grounded in trusted ownership tools.
          </p>
        </div>

        <div className="foundation__status" aria-label="Frontend foundation status">
          <span className="status-indicator" aria-hidden="true" />
          <div>
            <strong>Design foundation ready</strong>
            <span>Dashboard experience comes next</span>
          </div>
        </div>
      </section>

      <footer className="foundation__footer">
        <span>Customer Ownership Copilot</span>
        <span>Professional assistance, structured by trusted services</span>
      </footer>
    </main>
  )
}

export default App
