import { IoNavigateCircleOutline, IoPartlySunnyOutline, IoShieldCheckmarkOutline } from 'react-icons/io5'
import './App.css'

function App() {
  return (
    <div className="app-container">
      <header className="header">
        <div className="logo-container">
          <IoNavigateCircleOutline className="header-icon" size={36} />
          <div>
            <h1>Weather-Aware Truck Routing</h1>
            <p>Smart route risk and weather analysis system</p>
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
              <IoNavigateCircleOutline size={24} />
              <span>Multi-route Planning</span>
            </div>
            <div className="feature-item">
              <IoPartlySunnyOutline size={24} />
              <span>Weather and Heatmap (0-48h)</span>
            </div>
            <div className="feature-item">
              <IoShieldCheckmarkOutline size={24} />
              <span>Risk Evaluation and Load Rules</span>
            </div>
          </div>
        </section>
      </main>
    </div>
  )
}

export default App
