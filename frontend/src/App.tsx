import { Truck, CloudSun, ShieldCheck } from 'lucide-react'
import './App.css'

function App() {
  return (
    <div className="app-container">
      <header className="header">
        <div className="logo-container">
          <Truck className="header-icon" size={32} />
          <div>
            <h1>Weather-Aware Truck Routing</h1>
            <p>Smart route risk & weather analysis system</p>
          </div>
        </div>
      </header>

      <main className="main-content">
        <section className="welcome-card">
          <h2>Phase 1 Initialized</h2>
          <p>
            Backend (Django REST Framework) and Frontend (React + Vite + TypeScript + ESLint) ready.
          </p>
          <div className="features-preview">
            <div className="feature-item">
              <Truck size={24} />
              <span>Multi-route Planning</span>
            </div>
            <div className="feature-item">
              <CloudSun size={24} />
              <span>Weather & Heatmap (0-48h)</span>
            </div>
            <div className="feature-item">
              <ShieldCheck size={24} />
              <span>Risk Evaluation & Load Rules</span>
            </div>
          </div>
        </section>
      </main>
    </div>
  )
}

export default App
