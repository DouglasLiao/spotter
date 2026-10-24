import React, { useEffect, useMemo, useRef } from 'react'
import L from 'leaflet'
import 'leaflet.heat'
import { IoNavigateOutline, IoMapOutline } from 'react-icons/io5'
import type { RouteOption, LocationGeo, RiskLevel, HeatmapMetric, WeatherCorridor } from '../types/routing'

interface MapViewProps {
  origin: LocationGeo | null
  destination: LocationGeo | null
  routes: RouteOption[]
  selectedRouteId: string | number
  onSelectRoute: (routeId: string | number) => void
  hasTimeline?: boolean
  forecastHour: number
  corridor?: WeatherCorridor
  departureTime?: string
  heatmapMetric: HeatmapMetric
  onChangeHeatmapMetric: (metric: HeatmapMetric) => void
  isTripSimulationMode: boolean
  onToggleSimulationMode: () => void
}

function css(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

function riskColor(level: RiskLevel): string {
  return css(`--color-risk-${level.toLowerCase().replace(' ', '-')}`)
}

function text(value: string): HTMLElement {
  const element = document.createElement('div')
  element.textContent = value
  return element
}

function displayTime(iso?: string): string {
  return iso ? new Date(iso).toLocaleString('en-US', { timeZoneName: 'short' }) : 'Unavailable'
}

function removeHeatLayer(map: L.Map, layer: L.HeatLayer) {
  // leaflet.heat 0.2.0 leaves its animation frame queued after onRemove.
  const pending = layer as L.HeatLayer & { _frame?: number }
  if (pending._frame) L.Util.cancelAnimFrame(pending._frame)
  pending._frame = undefined
  map.removeLayer(layer)
}

const METRICS: { id: HeatmapMetric; label: string }[] = [
  { id: 'none', label: 'Off' }, { id: 'risk', label: 'Weather Risk' },
  { id: 'wind', label: 'Wind Speed' }, { id: 'precip', label: 'Rain / Snow' },
]

export const MapView: React.FC<MapViewProps> = ({
  origin, destination, routes, selectedRouteId, onSelectRoute, hasTimeline,
  forecastHour, corridor, departureTime, heatmapMetric, onChangeHeatmapMetric,
  isTripSimulationMode, onToggleSimulationMode,
}) => {
  const container = useRef<HTMLDivElement>(null)
  const mapRef = useRef<L.Map | null>(null)
  const routesRef = useRef<L.LayerGroup | null>(null)
  const checkpointRef = useRef<L.LayerGroup | null>(null)
  const unknownRef = useRef<L.LayerGroup | null>(null)
  const truckRef = useRef<L.LayerGroup | null>(null)
  const heatRef = useRef<L.HeatLayer | null>(null)
  const fittedRoutes = useRef<RouteOption[] | null>(null)
  const selected = routes.find((route) => String(route.id) === String(selectedRouteId)) ?? routes[0]

  const forecastPoints = useMemo(() => (corridor?.points ?? []).map((point) => ({
    ...point, forecast: point.hourly_forecast[Math.floor(forecastHour)],
  })), [corridor, forecastHour])
  const availableCount = forecastPoints.filter((point) => point.forecast?.available).length

  // Use distance along the polyline, rather than its unevenly spaced vertex indices.
  const truckPath = useMemo(() => {
    const coordinates = selected?.coordinates ?? []
    const path: { coordinate: [number, number]; distance: number }[] = []
    for (let index = 0; index < coordinates.length; index++) {
      const distance = index ? path[index - 1].distance + L.latLng(coordinates[index - 1]).distanceTo(L.latLng(coordinates[index])) : 0
      path.push({ coordinate: coordinates[index], distance })
    }
    return path
  }, [selected])

  useEffect(() => {
    if (!container.current) return
    const map = L.map(container.current, { center: [39.8283, -98.5795], zoom: 4, zoomControl: false })
    L.control.zoom({ position: 'bottomright' }).addTo(map)
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      maxZoom: 18, attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map)
    routesRef.current = L.layerGroup().addTo(map)
    checkpointRef.current = L.layerGroup().addTo(map)
    unknownRef.current = L.layerGroup().addTo(map)
    truckRef.current = L.layerGroup().addTo(map)
    mapRef.current = map
    const observer = new ResizeObserver(() => map.invalidateSize())
    observer.observe(container.current)
    return () => {
      observer.disconnect()
      if (heatRef.current) removeHeatLayer(map, heatRef.current)
      map.remove()
      mapRef.current = null
      heatRef.current = null
      fittedRoutes.current = null
    }
  }, [])

  useEffect(() => {
    const map = mapRef.current
    const layer = routesRef.current
    if (!map || !layer) return
    layer.clearLayers()
    const bounds = L.latLngBounds([])
    const ordered = [...routes.filter((route) => route !== selected), ...routes.filter((route) => route === selected)]
    ordered.forEach((route) => {
      route.coordinates.forEach((point) => bounds.extend(point))
      const line = L.polyline(route.coordinates, {
        color: css(route === selected ? '--color-primary' : '--color-border-dark'),
        weight: route === selected ? 6 : 4,
      }).bindTooltip(text(route.name), { sticky: true })
      line.on('click', () => onSelectRoute(route.id))
      layer.addLayer(line)
    })
    for (const [location, label] of [[origin, 'Origin'], [destination, 'Destination']] as const) {
      if (!location) continue
      L.circleMarker([location.lat, location.lon], {
        radius: 9, color: css('--color-white'), weight: 3,
        fillColor: css('--color-primary'), fillOpacity: 1,
      }).bindPopup(text(`${label}: ${location.formatted_address || location.address || location.name || label}`)).addTo(layer)
    }
    if (bounds.isValid() && fittedRoutes.current !== routes) {
      map.fitBounds(bounds, { padding: [40, 40] })
      fittedRoutes.current = routes
    }
  }, [routes, selected, origin, destination, onSelectRoute])

  // Checkpoints always show ETA weather: these are the values used for ranking.
  useEffect(() => {
    const layer = checkpointRef.current
    if (!layer) return
    layer.clearLayers()
    selected?.checkpoints.forEach((cp) => {
      const risk = cp.risk.overall_risk_label ?? 'Unknown'
      const measure = (value: number | null | undefined, unit: string) =>
        value == null ? 'Unavailable' : `${value.toFixed(2)} ${unit}`
      const popup = text([
        `Mile ${(cp.distance_from_start_miles ?? 0).toFixed(1)} — ${risk}`,
        `ETA: ${displayTime(cp.eta_iso ?? cp.eta)}`,
        `Wind: ${measure(cp.weather.wind_mph, 'mph')}`,
        `Rain: ${measure(cp.weather.rain_in_hr, 'in/h')}`,
        `Snow: ${measure(cp.weather.snow_in_hr, 'in/h')}`,
        cp.weather.unavailable_reason ?? '', cp.risk.load_reason ?? '',
      ].filter(Boolean).join('\n'))
      popup.className = 'checkpoint-popup'
      L.circleMarker([cp.lat, cp.lon], {
        className: 'checkpoint-marker',
        radius: 6, color: riskColor(risk), fillColor: riskColor(risk), fillOpacity: 1, weight: 2,
      }).bindPopup(popup, { minWidth: 220 }).addTo(layer)
    })
  }, [selected])

  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    unknownRef.current?.clearLayers()
    const heat: L.HeatLatLngTuple[] = []
    if (heatmapMetric !== 'none') {
      forecastPoints.forEach(({ lat, lon, forecast }) => {
        if (!forecast?.available || forecast.wind_mph == null || forecast.rain_in_hr == null || forecast.snow_in_hr == null) {
          L.circleMarker([lat, lon], { radius: 4, color: riskColor('Unknown'), fillOpacity: 0, weight: 1 })
            .bindTooltip(text('Corridor forecast unavailable')).addTo(unknownRef.current!)
          return
        }
        const intensity = heatmapMetric === 'risk' ? (forecast.risk_level ?? 0) / 5
          : heatmapMetric === 'wind' ? forecast.wind_mph / 55
            : Math.max(forecast.rain_in_hr / 1, forecast.snow_in_hr / 3)
        heat.push([lat, lon, Math.max(0, Math.min(1, intensity))])
      })
    }
    if (!heat.length) {
      if (heatRef.current) removeHeatLayer(map, heatRef.current)
      heatRef.current = null
      return
    }
    const options: L.HeatMapOptions = {
      radius: 35, blur: 22, maxZoom: 8, minOpacity: 0.25, max: 1,
      gradient: { 0.2: riskColor('Low'), 0.4: riskColor('Moderate'), 0.6: riskColor('High'),
        0.8: riskColor('Severe'), 1: riskColor('No Travel') },
    }
    if (heatRef.current) heatRef.current.setOptions(options).setLatLngs(heat)
    else heatRef.current = L.heatLayer(heat, options).addTo(map)
  }, [forecastPoints, heatmapMetric])

  useEffect(() => {
    const layer = truckRef.current
    if (!layer) return
    layer.clearLayers()
    if (!isTripSimulationMode || !selected || !truckPath.length) return
    const fraction = Math.min(1, forecastHour * 3600 / selected.duration_seconds)
    const target = fraction * truckPath[truckPath.length - 1].distance
    let end = truckPath.findIndex((point) => point.distance >= target)
    if (end < 0) end = truckPath.length - 1
    const p1 = truckPath[Math.max(0, end - 1)]
    const p2 = truckPath[end]
    const weight = p2.distance === p1.distance ? 0 : (target - p1.distance) / (p2.distance - p1.distance)
    const position: L.LatLngTuple = [p1.coordinate[0] + weight * (p2.coordinate[0] - p1.coordinate[0]),
      p1.coordinate[1] + weight * (p2.coordinate[1] - p1.coordinate[1])]
    L.circleMarker(position, { radius: 11, fillColor: css('--color-primary'), color: css('--color-white'),
      weight: 3, fillOpacity: 1 }).bindPopup(text(`Simulated progress: ${Math.round(fraction * 100)}%`)).addTo(layer)
  }, [forecastHour, isTripSimulationMode, selected, truckPath])

  return (
    <div className={`map-view-wrapper ${hasTimeline ? 'has-timeline' : ''}`}>
      {routes.length > 0 && (
        <>
          <div className="map-controls-toolbar">
            <div className="toolbar-metric-group">
              <span className="toolbar-label">Corridor Heatmap:</span>
              {METRICS.map(({ id, label }) => <button key={id} type="button"
                className={`toolbar-btn ${heatmapMetric === id ? 'toolbar-btn-active' : ''}`}
                onClick={() => onChangeHeatmapMetric(id)}>{label}</button>)}
            </div>
            <button type="button" className={`toolbar-btn ${isTripSimulationMode ? 'toolbar-btn-active' : ''}`}
              onClick={onToggleSimulationMode}>
              {isTripSimulationMode ? <IoNavigateOutline size={14} /> : <IoMapOutline size={14} />}
              <span>{isTripSimulationMode ? 'Truck Progress: Active' : 'Show Truck on Route'}</span>
            </button>
          </div>
          <div className="corridor-coverage" role="status">
            Checkpoints: ETA weather. Heatmap: {displayTime(departureTime ? new Date(new Date(departureTime).getTime() + forecastHour * 3600000).toISOString() : undefined)} (+{forecastHour}h).
            {' '}{availableCount}/{forecastPoints.length} grid points available; corridor ±{corridor?.half_width_miles ?? 0} mi,
            {' '}{corridor?.grid_spacing_miles ?? 0} mi spacing. Gray circles: unavailable.
          </div>
        </>
      )}
      <div ref={container} className="map-leaflet-container" />
    </div>
  )
}
