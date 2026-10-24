import { useState } from 'react'
import {
  IoNavigateCircleOutline,
  IoAlertCircleOutline,
  IoMapOutline,
  IoCloseOutline,
} from 'react-icons/io5'
import type { RoutePlanRequest, RoutePlanResponse, HeatmapMetric } from './types/routing'
import { planRoutes } from './services/api'
import { RouteForm } from './components/RouteForm'
import { RouteList } from './components/RouteList'
import { MapView } from './components/MapView'
import { RiskLegend } from './components/RiskLegend'
import { TimelineSlider } from './components/TimelineSlider'
import './App.css'

function App() {
  const [planData, setPlanData] = useState<RoutePlanResponse | null>(null)
  const [selectedRouteId, setSelectedRouteId] = useState<string | number>('route_1')
  const [isLoading, setIsLoading] = useState<boolean>(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [lastRequest, setLastRequest] = useState<RoutePlanRequest | null>(null)
  const [timelineOffsetHours, setTimelineOffsetHours] = useState<number>(0)
  const [showWelcomeOverlay, setShowWelcomeOverlay] = useState<boolean>(true)
  const [heatmapMetric, setHeatmapMetric] = useState<HeatmapMetric>('risk')
  const [isTripSimulationMode, setIsTripSimulationMode] = useState<boolean>(true)

  const handlePlanRoute = async (request: RoutePlanRequest) => {
    setIsLoading(true)
    setErrorMessage(null)
    setLastRequest(request)

    try {
      const response = await planRoutes(request)
      setPlanData(response)
      setSelectedRouteId(response.recommended_route_id || (response.routes[0]?.id ?? 'route_1'))
      setTimelineOffsetHours(0)
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'An unexpected error occurred while analyzing routes.'
      setErrorMessage(message)
    } finally {
      setIsLoading(false)
    }
  }

  const handleApplyForecastTime = (offsetHours: number) => {
    if (!lastRequest) return

    const baseDate = new Date(planData?.departure_time ?? lastRequest.departure_time ?? new Date().toISOString())
    const newDeparture = new Date(baseDate.getTime() + offsetHours * 60 * 60 * 1000)

    handlePlanRoute({
      ...lastRequest,
      departure_time: newDeparture.toISOString(),
    })
  }

  return (
    <div className="app-container">
      {/* Top Header */}
      <header className="app-header">
        <div className="header-brand">
          <IoNavigateCircleOutline size={32} className="brand-icon" />
          <div className="header-title-box">
            <h1>Weather-Aware Truck Routing</h1>
            <p>Corridor Weather Risk Analysis & Safe Navigation</p>
          </div>
        </div>

        <div className="header-badges">
          <span className="header-tech-badge">OSRM 3 Alternatives</span>
          <span className="header-tech-badge">Open-Meteo Hourly</span>
          <span className="header-tech-badge">5 Risk Levels</span>
        </div>
      </header>

      {/* Main Workspace: Left Sidebar + Right Map */}
      <div className="app-workspace">
        {/* Left Sidebar */}
        <aside className="app-sidebar">
          <div className="sidebar-content">
            {/* Error Message */}
            {errorMessage && (
              <div className="error-banner">
                <IoAlertCircleOutline size={20} className="error-banner-icon" />
                <span>{errorMessage}</span>
              </div>
            )}

            {planData?.warnings?.map((warning) => (
              <p className="weather-warning" role="status" key={warning}>{warning}</p>
            ))}

            {/* Input Form */}
            <RouteForm onSubmit={handlePlanRoute} isLoading={isLoading} />

            {/* Route Comparison List */}
            {planData && (
              <RouteList
                planData={planData}
                selectedRouteId={selectedRouteId}
                onSelectRoute={setSelectedRouteId}
              />
            )}

            {/* Static Risk & Load Matrix Legend */}
            <RiskLegend />
          </div>
        </aside>

        {/* Right Map Area */}
        <main className="app-map-area">
          <MapView
            origin={planData?.origin || null}
            destination={planData?.destination || null}
            routes={planData?.routes || []}
            selectedRouteId={selectedRouteId}
            onSelectRoute={setSelectedRouteId}
            hasTimeline={!!planData}
            forecastHour={timelineOffsetHours}
            corridor={planData?.corridor}
            departureTime={planData?.departure_time}
            heatmapMetric={heatmapMetric}
            onChangeHeatmapMetric={setHeatmapMetric}
            isTripSimulationMode={isTripSimulationMode}
            onToggleSimulationMode={() => setIsTripSimulationMode(!isTripSimulationMode)}
          />

          {/* Empty Prompt if no route loaded */}
          {!planData && !isLoading && showWelcomeOverlay && (
            <div className="map-empty-overlay">
              <div className="empty-overlay-header">
                <div className="empty-overlay-title">
                  <IoMapOutline size={18} />
                  <span>Ready to Plan Routes</span>
                </div>
                <button
                  type="button"
                  className="overlay-close-btn"
                  onClick={() => setShowWelcomeOverlay(false)}
                  title="Close message"
                  aria-label="Close message"
                >
                  <IoCloseOutline size={18} />
                </button>
              </div>
              <p className="empty-overlay-text">
                Select a corridor preset or input your origin, destination, and cargo weight to
                calculate 3 route options with real-time weather risk analysis.
              </p>
            </div>
          )}

          {/* Forecast Timeline Slider */}
          {planData && (
            <TimelineSlider
              offsetHours={timelineOffsetHours}
              onChangeOffset={setTimelineOffsetHours}
              baseDepartureTime={planData.departure_time}
              onApplyForecastTime={handleApplyForecastTime}
              isLoading={isLoading}
            />
          )}
        </main>
      </div>
    </div>
  )
}

export default App
