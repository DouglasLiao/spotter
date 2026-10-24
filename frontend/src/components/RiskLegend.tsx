import React from 'react'
import { IoShieldCheckmarkOutline, IoAlertCircleOutline } from 'react-icons/io5'
import type { RiskLevel } from '../types/routing'

interface RiskItem {
  level: RiskLevel
  label: string
  badgeClass: string
  dotClass: string
  description: string
  loadRuleNote: string
}

const RISK_DEFINITIONS: RiskItem[] = [
  {
    level: 'Low',
    label: 'Low Risk',
    badgeClass: 'risk-badge-low',
    dotClass: 'risk-dot-low',
    description: 'Wind < 20 mph, Rain < 0.1 in/h, Snow < 0.1 in/h',
    loadRuleNote: 'Safe driving conditions for standard truck payloads.',
  },
  {
    level: 'Moderate',
    label: 'Moderate',
    badgeClass: 'risk-badge-moderate',
    dotClass: 'risk-dot-moderate',
    description: 'Wind 20-34 mph, Rain 0.1-0.3 in/h, Snow 0.1-0.5 in/h',
    loadRuleNote: 'Exercise standard caution on open bridges and elevated corridors.',
  },
  {
    level: 'High',
    label: 'High Risk',
    badgeClass: 'risk-badge-high',
    dotClass: 'risk-dot-high',
    description: 'Wind 35-44 mph, Rain 0.3-0.5 in/h, Snow 0.5-1.0 in/h',
    loadRuleNote: 'Severe risk if payload exceeds 40,000 lbs due to crosswind sensitivity.',
  },
  {
    level: 'Severe',
    label: 'Severe Risk',
    badgeClass: 'risk-badge-severe',
    dotClass: 'risk-dot-severe',
    description: 'Wind 45-54 mph, Rain > 0.5 in/h, Snow > 1.0 in/h',
    loadRuleNote: 'No Travel if payload exceeds 30,000 lbs.',
  },
  {
    level: 'No Travel',
    label: 'No Travel',
    badgeClass: 'risk-badge-no-travel',
    dotClass: 'risk-dot-no-travel',
    description: 'Wind >= 55 mph or severe crosswind threshold exceeded',
    loadRuleNote: 'Critical rollover risk. Driving is prohibited along this checkpoint.',
  },
]

export const RiskLegend: React.FC = () => {
  return (
    <div className="risk-legend-container">
      <div className="risk-legend-header">
        <IoShieldCheckmarkOutline className="legend-icon" size={18} />
        <h3>Weather & Load Risk Matrix</h3>
      </div>
      <div className="risk-legend-list">
        {RISK_DEFINITIONS.map((item) => (
          <div key={item.level} className="risk-legend-item">
            <div className="risk-legend-badge-row">
              <span className={`risk-indicator-dot ${item.dotClass}`} />
              <span className={`risk-badge ${item.badgeClass}`}>{item.label}</span>
            </div>
            <div className="risk-legend-details">
              <p className="risk-legend-weather">{item.description}</p>
              <p className="risk-legend-rule">{item.loadRuleNote}</p>
            </div>
          </div>
        ))}
      </div>
      <div className="risk-legend-footer">
        <IoAlertCircleOutline size={14} className="legend-rule-icon" />
        <span>Load rules dynamically elevate risk classification based on cargo weight (lbs).</span>
      </div>
    </div>
  )
}
