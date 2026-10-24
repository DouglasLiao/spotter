import React, { useEffect, useRef } from 'react'
import L from 'leaflet'
import 'leaflet.heat'
import {
  IoShieldCheckmarkOutline,
  IoSpeedometerOutline,
  IoRainyOutline,
  IoEyeOffOutline,
  IoNavigateOutline,
  IoMapOutline,
} from 'react-icons/io5'
import type { RouteOption, Checkpoint, LocationGeo, RiskLevel, HeatmapMetric } from '../types/routing'

interface MapViewProps {
  origin: LocationGeo | null
  destination: LocationGeo | null
  routes: RouteOption[]
  selectedRouteId: string | number
  onSelectRoute: (routeId: string | number) => void
  hasTimeline?: boolean
  forecastHour: number
  heatmapMetric: HeatmapMetric
  onChangeHeatmapMetric: (metric: HeatmapMetric) => void
  isTripSimulationMode: boolean
  onToggleSimulationMode: () => void
}

function getCssVar(varName: string, fallback: string): string {
  if (typeof window === 'undefined') return fallback
  const val = getComputedStyle(document.documentElement).getPropertyValue(varName).trim()
  return val || fallback
}

function getRiskColor(level: RiskLevel): { fill: string; border: string; badgeClass: string } {
  switch (level) {
    case 'Low':
      return {
        fill: getCssVar('--color-risk-low', '#10b981'),
        border: getCssVar('--color-risk-low-text', '#065f46'),
        badgeClass: 'risk-badge-low',
      }
    case 'Moderate':
      return {
        fill: getCssVar('--color-risk-moderate', '#f59e0b'),
        border: getCssVar('--color-risk-moderate-text', '#92400e'),
        badgeClass: 'risk-badge-moderate',
      }
    case 'High':
      return {
        fill: getCssVar('--color-risk-high', '#f97316'),
        border: getCssVar('--color-risk-high-text', '#9a3412'),
        badgeClass: 'risk-badge-high',
      }
    case 'Severe':
      return {
        fill: getCssVar('--color-risk-severe', '#ef4444'),
        border: getCssVar('--color-risk-severe-text', '#991b1b'),
        badgeClass: 'risk-badge-severe',
      }
    case 'No Travel':
      return {
        fill: getCssVar('--color-risk-no-travel', '#7f1d1d'),
        border: getCssVar('--color-risk-no-travel-text', '#450a0a'),
        badgeClass: 'risk-badge-no-travel',
      }
    default:
      return {
        fill: getCssVar('--color-risk-low', '#10b981'),
        border: getCssVar('--color-risk-low-text', '#065f46'),
        badgeClass: 'risk-badge-low',
      }
  }
}

export const MapView: React.FC<MapViewProps> = ({
  origin,
  destination,
  routes,
  selectedRouteId,
  onSelectRoute,
  hasTimeline,
  forecastHour,
  heatmapMetric,
  onChangeHeatmapMetric,
  isTripSimulationMode,
  onToggleSimulationMode,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null)
  const mapInstanceRef = useRef<L.Map | null>(null)
  const routesLayerGroupRef = useRef<L.LayerGroup | null>(null)
  const checkpointsLayerGroupRef = useRef<L.LayerGroup | null>(null)
  const truckLayerGroupRef = useRef<L.LayerGroup | null>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const heatLayerRef = useRef<any>(null)

  // 1. Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return

    const map = L.map(mapContainerRef.current, {
      center: [39.8283, -98.5795],
      zoom: 4,
      zoomControl: false,
    })

    // Place zoom control in the bottom right corner
    L.control.zoom({ position: 'bottomright' }).addTo(map)

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18,
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map)

    routesLayerGroupRef.current = L.layerGroup().addTo(map)
    checkpointsLayerGroupRef.current = L.layerGroup().addTo(map)
    truckLayerGroupRef.current = L.layerGroup().addTo(map)
    mapInstanceRef.current = map

    return () => {
      map.remove()
      mapInstanceRef.current = null
      routesLayerGroupRef.current = null
      checkpointsLayerGroupRef.current = null
      truckLayerGroupRef.current = null
      heatLayerRef.current = null
    }
  }, [])

  // 2. Render Static Route Polylines and Landmark Markers (Only when routes/selection changes)
  useEffect(() => {
    const map = mapInstanceRef.current
    const routesLayer = routesLayerGroupRef.current
    if (!map || !routesLayer) return

    routesLayer.clearLayers()

    if (!routes || routes.length === 0) return

    const bounds = L.latLngBounds([])

    // Draw Inactive / Alternative Routes first (underneath)
    routes.forEach((route) => {
      if (String(route.id) === String(selectedRouteId)) return

      const latLngs = route.coordinates.map((c) => L.latLng(c[0], c[1]))
      latLngs.forEach((pt) => bounds.extend(pt))

      const polyline = L.polyline(latLngs, {
        color: getCssVar('--color-border-dark', '#94a3b8'),
        weight: 4,
        opacity: 1,
      })

      polyline.on('click', () => onSelectRoute(route.id))
      polyline.bindTooltip(`Alternative: ${route.name} (Click to select)`, {
        sticky: true,
      })

      routesLayer.addLayer(polyline)
    })

    // Draw Active / Selected Route on top
    const selectedRoute =
      routes.find((r) => String(r.id) === String(selectedRouteId)) || routes[0]

    if (selectedRoute) {
      const activeLatLngs = selectedRoute.coordinates.map((c) => L.latLng(c[0], c[1]))
      activeLatLngs.forEach((pt) => bounds.extend(pt))

      const activePolyline = L.polyline(activeLatLngs, {
        color: getCssVar('--color-primary', '#1d4ed8'),
        weight: 6,
        opacity: 1,
      })

      const durationText =
        selectedRoute.duration_formatted ||
        (selectedRoute.duration_hours
          ? `${Math.floor(selectedRoute.duration_hours)}h ${Math.round(
              (selectedRoute.duration_hours % 1) * 60,
            )}m`
          : '')

      activePolyline.bindTooltip(
        `Active: ${selectedRoute.name} ${durationText ? `(${durationText})` : ''}`,
        { sticky: true },
      )
      routesLayer.addLayer(activePolyline)
    }

    // Origin Marker
    if (origin) {
      const originAddress = origin.formatted_address || origin.address || origin.name || 'Origin'
      const originMarker = L.circleMarker([origin.lat, origin.lon], {
        radius: 9,
        fillColor: getCssVar('--color-risk-low', '#10b981'),
        color: getCssVar('--color-white', '#ffffff'),
        weight: 3,
        opacity: 1,
        fillOpacity: 1,
      })
      originMarker.bindPopup(`<strong>Origin:</strong> ${originAddress}`)
      routesLayer.addLayer(originMarker)
      bounds.extend([origin.lat, origin.lon])
    }

    // Destination Marker
    if (destination) {
      const destAddress =
        destination.formatted_address || destination.address || destination.name || 'Destination'
      const destMarker = L.circleMarker([destination.lat, destination.lon], {
        radius: 9,
        fillColor: getCssVar('--color-primary-hover', '#1e40af'),
        color: getCssVar('--color-white', '#ffffff'),
        weight: 3,
        opacity: 1,
        fillOpacity: 1,
      })
      destMarker.bindPopup(`<strong>Destination:</strong> ${destAddress}`)
      routesLayer.addLayer(destMarker)
      bounds.extend([destination.lat, destination.lon])
    }

    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [40, 40] })
    }
  }, [routes, selectedRouteId, origin, destination, onSelectRoute])

  // 3. Dynamic Checkpoints, Heatmap & Truck Simulation (Updates instantaneously when forecastHour or metric changes)
  useEffect(() => {
    const map = mapInstanceRef.current
    const cpLayer = checkpointsLayerGroupRef.current
    const truckLayer = truckLayerGroupRef.current
    if (!map || !cpLayer || !truckLayer) return

    cpLayer.clearLayers()
    truckLayer.clearLayers()

    const selectedRoute =
      routes.find((r) => String(r.id) === String(selectedRouteId)) || routes[0]

    if (!selectedRoute) {
      if (heatLayerRef.current) {
        map.removeLayer(heatLayerRef.current)
        heatLayerRef.current = null
      }
      return
    }

    const heatPoints: [number, number, number][] = []

    // A. Render Dynamic Checkpoints based on forecastHour
    selectedRoute.checkpoints.forEach((cp: Checkpoint) => {
      // Find hourly forecast at forecastHour or fallback to primary checkpoint data
      const hf = cp.hourly_forecast?.find((h) => h.hour === forecastHour)

      const windVal = hf?.wind_mph ?? (cp.weather.wind_mph ?? cp.weather.wind_speed_mph ?? 0)
      const rainVal = hf?.rain_in_hr ?? (cp.weather.rain_in_hr ?? cp.weather.rain_in_per_hr ?? 0)
      const snowVal = hf?.snow_in_hr ?? (cp.weather.snow_in_hr ?? cp.weather.snow_in_per_hr ?? 0)
      const riskLevel: RiskLevel =
        hf?.risk_label || cp.risk.overall_risk_label || cp.risk.level || 'Low'
      const loadPenalty = hf?.load_penalty_applied ?? cp.risk.load_penalty_applied

      const riskColors = getRiskColor(riskLevel)

      const marker = L.circleMarker([cp.lat, cp.lon], {
        radius: 6,
        fillColor: riskColors.fill,
        color: riskColors.border,
        weight: 2,
        opacity: 1,
        fillOpacity: 1,
      })

      const distanceVal = cp.distance_from_start_miles ?? cp.distance_from_origin_miles ?? 0
      const timeLabel = hf?.time
        ? new Date(hf.time).toLocaleString('en-US', {
            weekday: 'short',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
          })
        : `Hour +${forecastHour}`

      const loadPenaltyNotice = loadPenalty
        ? `<div class="popup-load-penalty">Load Rollover Risk Penalty Applied</div>`
        : ''

      const popupContent = `
        <div class="leaflet-popup-card">
          <div class="popup-card-header">
            <span class="popup-checkpoint-id">Mile ${distanceVal.toFixed(1)}</span>
            <span class="risk-badge ${riskColors.badgeClass}">${riskLevel}</span>
          </div>
          <div class="popup-eta-row">
            <strong>Forecast Time:</strong> <span>${timeLabel} (+${forecastHour}h)</span>
          </div>
          <div class="popup-weather-grid">
            <div class="weather-col">
              <span class="w-label">Wind</span>
              <span class="w-val">${windVal.toFixed(1)} mph</span>
            </div>
            <div class="weather-col">
              <span class="w-label">Rain</span>
              <span class="w-val">${rainVal.toFixed(2)} in/h</span>
            </div>
            <div class="weather-col">
              <span class="w-label">Snow</span>
              <span class="w-val">${snowVal.toFixed(2)} in/h</span>
            </div>
          </div>
          ${loadPenaltyNotice}
        </div>
      `

      marker.bindPopup(popupContent, { minWidth: 220 })
      cpLayer.addLayer(marker)

      // Calculate Heatmap Point
      if (heatmapMetric !== 'none') {
        let intensity = 0.2
        if (heatmapMetric === 'risk') {
          const score =
            riskLevel === 'No Travel'
              ? 1.0
              : riskLevel === 'Severe'
                ? 0.85
                : riskLevel === 'High'
                  ? 0.65
                  : riskLevel === 'Moderate'
                    ? 0.45
                    : 0.2
          intensity = score
        } else if (heatmapMetric === 'wind') {
          intensity = Math.min(1.0, Math.max(0.1, windVal / 55.0))
        } else if (heatmapMetric === 'precip') {
          intensity = Math.min(1.0, Math.max(0.1, (rainVal + snowVal) / 0.8))
        }

        heatPoints.push([cp.lat, cp.lon, intensity])
      }
    })

    // B. Build & Update Heatmap Layer
    if (heatmapMetric === 'none' || heatPoints.length === 0) {
      if (heatLayerRef.current) {
        map.removeLayer(heatLayerRef.current)
        heatLayerRef.current = null
      }
    } else {
      // Add intermediate interpolated points along corridor for smoother visual ribbon
      const denseHeatPoints: [number, number, number][] = []
      for (let i = 0; i < heatPoints.length - 1; i++) {
        const p1 = heatPoints[i]
        const p2 = heatPoints[i + 1]
        denseHeatPoints.push(p1)
        // Midpoint
        denseHeatPoints.push([
          (p1[0] + p2[0]) / 2,
          (p1[1] + p2[1]) / 2,
          (p1[2] + p2[2]) / 2,
        ])
      }
      if (heatPoints.length > 0) {
        denseHeatPoints.push(heatPoints[heatPoints.length - 1])
      }

      if (heatLayerRef.current) {
        heatLayerRef.current.setLatLngs(denseHeatPoints)
      } else {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const heatLayer = (L as any).heatLayer(denseHeatPoints, {
          radius: 35,
          blur: 22,
          maxZoom: 13,
          minOpacity: 0.35,
          gradient:
            heatmapMetric === 'wind'
              ? { 0.2: '#93c5fd', 0.5: '#3b82f6', 0.75: '#f97316', 1.0: '#ef4444' }
              : heatmapMetric === 'precip'
                ? { 0.2: '#6ee7b7', 0.5: '#38bdf8', 0.8: '#6366f1', 1.0: '#4338ca' }
                : { 0.2: '#10b981', 0.45: '#f59e0b', 0.7: '#f97316', 0.9: '#ef4444', 1.0: '#7f1d1d' },
        }).addTo(map)
        heatLayerRef.current = heatLayer
      }
    }

    // C. Simulated Truck Position
    if (isTripSimulationMode && selectedRoute.coordinates.length > 0) {
      const totalHours = (selectedRoute.duration_seconds || 3600) / 3600
      const progressFraction = Math.min(1.0, Math.max(0, forecastHour / totalHours))
      const coords = selectedRoute.coordinates
      const targetIdx = Math.min(coords.length - 1, Math.floor(progressFraction * (coords.length - 1)))
      const truckPos = coords[targetIdx]

      const truckMarker = L.circleMarker([truckPos[0], truckPos[1]], {
        radius: 11,
        fillColor: getCssVar('--color-primary', '#1d4ed8'),
        color: getCssVar('--color-white', '#ffffff'),
        weight: 3,
        opacity: 1,
        fillOpacity: 1,
      })

      const milesCompleted = Math.round(progressFraction * selectedRoute.distance_miles)
      const pct = Math.round(progressFraction * 100)

      truckMarker.bindPopup(`
        <div class="leaflet-popup-card">
          <div class="popup-card-header">
            <span class="popup-checkpoint-id">Simulated Truck Position</span>
            <span class="risk-badge risk-badge-low">${pct}% Progress</span>
          </div>
          <div class="popup-eta-row">
            <strong>Elapsed Travel Time:</strong> +${forecastHour}h / ${selectedRoute.duration_formatted}
          </div>
          <div class="popup-eta-row">
            <strong>Distance Traveled:</strong> ${milesCompleted} mi / ${selectedRoute.distance_miles.toFixed(0)} mi
          </div>
        </div>
      `)

      truckLayer.addLayer(truckMarker)
    }
  }, [routes, selectedRouteId, forecastHour, heatmapMetric, isTripSimulationMode])

  return (
    <div className={`map-view-wrapper ${hasTimeline ? 'has-timeline' : ''}`}>
      {/* Top Map Interactive Control Bar */}
      {routes && routes.length > 0 && (
        <div className="map-controls-toolbar">
          <div className="toolbar-metric-group">
            <span className="toolbar-label">Corridor Heatmap:</span>
            <button
              type="button"
              className={`toolbar-btn ${heatmapMetric === 'none' ? 'toolbar-btn-active' : ''}`}
              onClick={() => onChangeHeatmapMetric('none')}
              title="Hide Heatmap Layer"
            >
              <IoEyeOffOutline size={14} />
              <span>Off</span>
            </button>
            <button
              type="button"
              className={`toolbar-btn ${heatmapMetric === 'risk' ? 'toolbar-btn-active' : ''}`}
              onClick={() => onChangeHeatmapMetric('risk')}
              title="Show Risk Severity Heatmap"
            >
              <IoShieldCheckmarkOutline size={14} />
              <span>Weather Risk</span>
            </button>
            <button
              type="button"
              className={`toolbar-btn ${heatmapMetric === 'wind' ? 'toolbar-btn-active' : ''}`}
              onClick={() => onChangeHeatmapMetric('wind')}
              title="Show Wind Speed Intensity Heatmap"
            >
              <IoSpeedometerOutline size={14} />
              <span>Wind Speed</span>
            </button>
            <button
              type="button"
              className={`toolbar-btn ${heatmapMetric === 'precip' ? 'toolbar-btn-active' : ''}`}
              onClick={() => onChangeHeatmapMetric('precip')}
              title="Show Precipitation & Snow Heatmap"
            >
              <IoRainyOutline size={14} />
              <span>Precipitation</span>
            </button>
          </div>

          <div className="toolbar-mode-group">
            <button
              type="button"
              className={`toolbar-btn ${isTripSimulationMode ? 'toolbar-btn-active' : ''}`}
              onClick={onToggleSimulationMode}
              title="Toggle Truck Progress Marker along route"
            >
              {isTripSimulationMode ? (
                <>
                  <IoNavigateOutline size={14} />
                  <span>Truck Progress: Active</span>
                </>
              ) : (
                <>
                  <IoMapOutline size={14} />
                  <span>Show Truck on Route</span>
                </>
              )}
            </button>

            <span className="toolbar-sim-badge">Simulating: +{forecastHour}h</span>
          </div>
        </div>
      )}

      <div ref={mapContainerRef} className="map-leaflet-container" />
    </div>
  )
}
