import React from 'react'
import {
  IoCheckmarkCircleOutline,
  IoTimeOutline,
  IoGitCommitOutline,
  IoAlertCircleOutline,
  IoShieldOutline,
} from 'react-icons/io5'
import type { RouteOption, RiskLevel } from '../types/routing'

interface RouteCardProps {
  route: RouteOption
  isSelected: boolean
  onSelect: (routeId: string | number) => void
}

function getRiskBadgeClass(level: RiskLevel): string {
  switch (level) {
    case 'Low':
      return 'risk-badge-low'
    case 'Moderate':
      return 'risk-badge-moderate'
    case 'High':
      return 'risk-badge-high'
    case 'Severe':
      return 'risk-badge-severe'
    case 'No Travel':
      return 'risk-badge-no-travel'
    default:
      return 'risk-badge-unknown'
  }
}

export const RouteCard: React.FC<RouteCardProps> = ({ route, isSelected, onSelect }) => {
  const { risk_summary } = route
  const isRecommended = route.is_recommended

  const totalMiles = route.distance_miles || 1
  const severePct = Math.round((risk_summary.severe_miles / totalMiles) * 100)
  const highPct = Math.round((risk_summary.high_miles / totalMiles) * 100)
  const modPct = Math.round((risk_summary.moderate_miles / totalMiles) * 100)
  const lowPct = Math.round((risk_summary.low_miles / totalMiles) * 100)
  const unknownPct = Math.round(((risk_summary.unknown_miles ?? 0) / totalMiles) * 100)

  const peakRisk: RiskLevel =
    risk_summary.max_risk_level || risk_summary.highest_risk_level || 'Unknown'

  const riskScore =
    risk_summary.weighted_risk_score ?? risk_summary.average_risk_score

  const durationFormatted =
    route.duration_formatted ||
    (route.duration_hours
      ? `${Math.floor(route.duration_hours)}h ${Math.round((route.duration_hours % 1) * 60)}m`
      : `${Math.round(route.duration_seconds / 3600)}h`)

  return (
    <div
      className={`route-card ${isSelected ? 'route-card-selected' : ''} ${
        isRecommended ? 'route-card-recommended' : ''
      }`}
      onClick={() => onSelect(route.id)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          onSelect(route.id)
        }
      }}
    >
      {/* Top Banner for Recommended Route */}
      {isRecommended && (
        <div className="recommended-badge-banner">
          <IoCheckmarkCircleOutline size={16} />
          <span>RECOMMENDED ROUTE</span>
        </div>
      )}

      <div className="route-card-header">
        <div className="route-title-col">
          <span className="route-option-label">{String(route.id).replace('_', ' ')}</span>
          <h3 className="route-name">{route.name}</h3>
        </div>
        <span className={`risk-badge ${getRiskBadgeClass(peakRisk)}`}>
          {peakRisk} Peak
        </span>
      </div>

      {/* Primary Metrics: Duration and Distance */}
      <div className="route-metrics-grid">
        <div className="metric-box">
          <IoTimeOutline size={16} className="metric-icon" />
          <div className="metric-content">
            <span className="metric-label">Travel Time</span>
            <span className="metric-value">{durationFormatted}</span>
          </div>
        </div>

        <div className="metric-box">
          <IoGitCommitOutline size={16} className="metric-icon" />
          <div className="metric-content">
            <span className="metric-label">Distance</span>
            <span className="metric-value">{route.distance_miles.toFixed(1)} mi</span>
          </div>
        </div>

        <div className="metric-box">
          <IoShieldOutline size={16} className="metric-icon" />
          <div className="metric-content">
            <span className="metric-label">Avg Risk</span>
            <span className="metric-value">{riskScore == null ? 'Unknown' : `${riskScore.toFixed(2)} / 5.0`}</span>
          </div>
        </div>
      </div>

      {/* Risk Distribution Breakdown Bar */}
      <div className="risk-distribution-container">
        <div className="risk-distribution-header">
          <span className="distribution-label">Risk Exposure by Distance:</span>
          <span className="distribution-severe-miles">
            {risk_summary.severe_miles > 0
              ? `${risk_summary.severe_miles.toFixed(1)} mi Severe`
              : '0 mi Severe'}
          </span>
        </div>

        {/* Visual Solid Segmented Bar */}
        <div className="segmented-risk-bar">
          <div className="segment-unknown" style={{ width: `${unknownPct}%` }} title={`Unknown: ${(risk_summary.unknown_miles ?? 0).toFixed(1)} mi`} />
          <div className="segment-low" style={{ width: `${lowPct}%` }} title={`Low: ${risk_summary.low_miles.toFixed(1)} mi`} />
          <div className="segment-moderate" style={{ width: `${modPct}%` }} title={`Moderate: ${risk_summary.moderate_miles.toFixed(1)} mi`} />
          <div className="segment-high" style={{ width: `${highPct}%` }} title={`High: ${risk_summary.high_miles.toFixed(1)} mi`} />
          <div className="segment-severe" style={{ width: `${severePct}%` }} title={`Severe: ${risk_summary.severe_miles.toFixed(1)} mi`} />
        </div>

        {risk_summary.weather_complete === false && <p className="weather-warning">Weather incomplete — route excluded from recommendations. Unknown: {(risk_summary.unknown_miles ?? 0).toFixed(1)} mi.</p>}

        {/* Numeric Legend Pills */}
        <div className="risk-numbers-row">
          <span className="num-pill num-pill-low">Low: {risk_summary.low_miles.toFixed(0)}m</span>
          <span className="num-pill num-pill-mod">Mod: {risk_summary.moderate_miles.toFixed(0)}m</span>
          <span className="num-pill num-pill-high">High: {risk_summary.high_miles.toFixed(0)}m</span>
          <span className="num-pill num-pill-sev">Sev: {risk_summary.severe_miles.toFixed(0)}m</span>
          {risk_summary.no_travel_miles > 0 && (
            <span className="num-pill num-pill-notravel">
              No Travel: {risk_summary.no_travel_miles.toFixed(0)}m
            </span>
          )}
        </div>
      </div>

      {/* Recommendation Reason Note */}
      {route.recommendation_reason && (
        <div className="recommendation-reason-box">
          <IoAlertCircleOutline size={16} className="reason-icon" />
          <p>{route.recommendation_reason}</p>
        </div>
      )}
    </div>
  )
}
