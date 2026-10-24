import React, { useState } from 'react'
import {
  IoLocationOutline,
  IoNavigateOutline,
  IoCalendarOutline,
  IoScaleOutline,
  IoSpeedometerOutline,
  IoSearchOutline,
  IoSwapVerticalOutline,
  IoFlashOutline,
} from 'react-icons/io5'
import type { RoutePlanRequest } from '../types/routing'

interface RouteFormProps {
  onSubmit: (request: RoutePlanRequest) => void
  isLoading: boolean
}

interface CorridorPreset {
  label: string
  origin: string
  destination: string
  loadWeight: number
}

const PRESET_CORRIDORS: CorridorPreset[] = [
  {
    label: 'Chicago -> Denver (Heavy 42k)',
    origin: 'Chicago, IL',
    destination: 'Denver, CO',
    loadWeight: 42000,
  },
  {
    label: 'Atlanta -> Dallas (Mid 32k)',
    origin: 'Atlanta, GA',
    destination: 'Dallas, TX',
    loadWeight: 32000,
  },
  {
    label: 'Seattle -> Salt Lake City (Heavy 45k)',
    origin: 'Seattle, WA',
    destination: 'Salt Lake City, UT',
    loadWeight: 45000,
  },
  {
    label: 'Los Angeles -> Phoenix (Light 18k)',
    origin: 'Los Angeles, CA',
    destination: 'Phoenix, AZ',
    loadWeight: 18000,
  },
]

export const RouteForm: React.FC<RouteFormProps> = ({ onSubmit, isLoading }) => {
  const [origin, setOrigin] = useState('Chicago, IL')
  const [destination, setDestination] = useState('Denver, CO')
  const [loadWeight, setLoadWeight] = useState(42000)
  const [sampleInterval, setSampleInterval] = useState<number>(25)

  // Default departure time formatted for datetime-local input (YYYY-MM-DDTHH:mm)
  const [departureTime, setDepartureTime] = useState(() => {
    const now = new Date()
    now.setMinutes(now.getMinutes() - now.getTimezoneOffset())
    return now.toISOString().slice(0, 16)
  })

  const handleSwapLocations = () => {
    setOrigin(destination)
    setDestination(origin)
  }

  const handleApplyPreset = (preset: CorridorPreset) => {
    setOrigin(preset.origin)
    setDestination(preset.destination)
    setLoadWeight(preset.loadWeight)
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!origin.trim() || !destination.trim()) return

    const departureIso = new Date(departureTime).toISOString()

    onSubmit({
      origin: origin.trim(),
      destination: destination.trim(),
      departure_time: departureIso,
      load_weight: Number(loadWeight),
      sample_interval_miles: sampleInterval,
    })
  }

  return (
    <form className="route-form" onSubmit={handleSubmit}>
      <div className="form-section-title">
        <IoSearchOutline size={18} className="section-icon" />
        <h2>Route & Cargo Parameters</h2>
      </div>

      {/* Preset Corridors */}
      <div className="form-presets-container">
        <div className="preset-header">
          <IoFlashOutline size={14} className="preset-icon" />
          <span>Quick Corridors</span>
        </div>
        <div className="preset-pill-list">
          {PRESET_CORRIDORS.map((preset) => (
            <button
              key={preset.label}
              type="button"
              className="preset-pill"
              onClick={() => handleApplyPreset(preset)}
              disabled={isLoading}
            >
              {preset.label}
            </button>
          ))}
        </div>
      </div>

      {/* Origin & Destination Inputs */}
      <div className="form-fields-group">
        <div className="form-field">
          <label htmlFor="origin-input" className="form-label">
            <IoLocationOutline size={16} className="field-icon" />
            Origin Location
          </label>
          <input
            id="origin-input"
            type="text"
            className="form-input"
            placeholder="City, State or Address (e.g. Chicago, IL)"
            value={origin}
            onChange={(e) => setOrigin(e.target.value)}
            required
            disabled={isLoading}
          />
        </div>

        <div className="swap-locations-row">
          <button
            type="button"
            className="swap-button"
            onClick={handleSwapLocations}
            title="Swap Origin and Destination"
            disabled={isLoading}
          >
            <IoSwapVerticalOutline size={18} />
          </button>
        </div>

        <div className="form-field">
          <label htmlFor="dest-input" className="form-label">
            <IoNavigateOutline size={16} className="field-icon" />
            Destination Location
          </label>
          <input
            id="dest-input"
            type="text"
            className="form-input"
            placeholder="City, State or Address (e.g. Denver, CO)"
            value={destination}
            onChange={(e) => setDestination(e.target.value)}
            required
            disabled={isLoading}
          />
        </div>
      </div>

      {/* Departure & Load Weight */}
      <div className="form-row-two-col">
        <div className="form-field">
          <label htmlFor="departure-input" className="form-label">
            <IoCalendarOutline size={16} className="field-icon" />
            Departure Time
          </label>
          <input
            id="departure-input"
            type="datetime-local"
            className="form-input"
            value={departureTime}
            onChange={(e) => setDepartureTime(e.target.value)}
            required
            disabled={isLoading}
          />
        </div>

        <div className="form-field">
          <label htmlFor="weight-input" className="form-label">
            <IoScaleOutline size={16} className="field-icon" />
            Load Weight (lbs)
          </label>
          <input
            id="weight-input"
            type="number"
            min="0"
            step="500"
            className="form-input"
            placeholder="42000"
            value={loadWeight}
            onChange={(e) => setLoadWeight(Number(e.target.value))}
            required
            disabled={isLoading}
          />
          <div className="weight-presets-row">
            <button
              type="button"
              className="weight-mini-pill"
              onClick={() => setLoadWeight(15000)}
              disabled={isLoading}
            >
              15k Light
            </button>
            <button
              type="button"
              className="weight-mini-pill"
              onClick={() => setLoadWeight(32000)}
              disabled={isLoading}
            >
              32k Mid
            </button>
            <button
              type="button"
              className="weight-mini-pill"
              onClick={() => setLoadWeight(42000)}
              disabled={isLoading}
            >
              42k Heavy
            </button>
          </div>
        </div>
      </div>

      {/* Sampling Interval Selector */}
      <div className="form-field">
        <label className="form-label">
          <IoSpeedometerOutline size={16} className="field-icon" />
          Checkpoint Interval: {sampleInterval} miles
        </label>
        <div className="interval-selector">
          {[10, 25, 50].map((interval) => (
            <button
              key={interval}
              type="button"
              className={`interval-pill ${sampleInterval === interval ? 'interval-pill-active' : ''}`}
              onClick={() => setSampleInterval(interval)}
              disabled={isLoading}
            >
              {interval} mi
            </button>
          ))}
        </div>
      </div>

      {/* Submit Button */}
      <button type="submit" className="submit-button" disabled={isLoading}>
        {isLoading ? (
          <span>Analyzing Corridors & Weather...</span>
        ) : (
          <>
            <IoSearchOutline size={18} />
            <span>Calculate & Compare Routes</span>
          </>
        )}
      </button>
    </form>
  )
}
